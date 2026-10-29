// @vitest-environment jsdom
// 읽기 화면의 '다시 듣기' 흐름. 서버·저장소·오디오는 가짜로 바꾼다
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import type { Segment, StoryKey } from "../api";
import type { SavedStory } from "../storage";

const fake = vi.hoisted(() => {
  let token = 0;
  const player = {
    src: "", playbackRate: 1, duration: 10, currentTime: 0,
    onended: null as null | (() => void), onloadedmetadata: null, ontimeupdate: null,
    play: vi.fn(() => Promise.resolve()), pause: vi.fn(),
  };
  return {
    player,
    audio: {
      player,
      playToken: () => ++token,
      isCurrent: (t: number) => t === token,
      stopAll: () => { token++; },
      speak: vi.fn(() => Promise.resolve()),
      getSpeed: () => "slow",
      setSpeed: vi.fn(),
      SPEEDS: { slow: 0.85, normal: 1 },
    },
    getAudio: vi.fn(),
    fetchSegmentAudio: vi.fn(),
    sendEvent: vi.fn(),
  };
});

vi.mock("../audio", () => fake.audio);
vi.mock("../storage", () => ({
  getAudio: fake.getAudio, saveAudio: vi.fn(), saveStory: vi.fn(), getAnonId: () => "anon",
}));
vi.mock("../api", async (orig) => ({
  ...(await orig<typeof import("../api")>()),
  fetchSegmentAudio: fake.fetchSegmentAudio, nextSegment: vi.fn(), sendEvent: fake.sendEvent,
}));

import { ApiError } from "../api";
import Reading from "./Reading";

const scene = { background: "forest", time: "day", characters: [{ id: "fox", state: "idle" }], objects: [] };
const seg = (type: Segment["type"], choices: string[]): Segment => ({
  type,
  pages: [{ text: `${type} 1`, scene, mood: "calm", sfx: null }, { text: `${type} 2`, scene, mood: "calm", sfx: null }],
  choices: choices.map((id) => ({ kind: "item", id, label: id })),
});
const story: StoryKey = { id: "s1", cards: ["fox"], choice_count: 2, voice: { provider: "gemini", model: "m", voice: "Kore" } };
const done: SavedStory = {
  story, createdAt: 1, done: true, chosen: ["bear", "cake"],
  segments: [seg("intro", ["bear", "owl", "moon"]), seg("middle", ["cake", "map", "key"]), seg("ending", [])]
    .map((segment, i) => ({ segment, sig: `sig${i}` })),
};

beforeEach(() => {
  vi.clearAllMocks();
  URL.createObjectURL = vi.fn(() => "blob:x");
  URL.revokeObjectURL = vi.fn();
});
afterEach(cleanup);

const flush = () => act(async () => { await new Promise((r) => setTimeout(r, 0)); });

async function openAndReplay() {
  render(<Reading saved={done} resume onUpdate={vi.fn()} onHome={vi.fn()} onNew={vi.fn()} />);
  await flush();
  fireEvent.click(screen.getByText(/다시 듣기/));
  await flush();
}

test("replay plays each segment once and does not replay the ending", async () => {
  fake.getAudio.mockResolvedValue(new Blob(["mp3"]));
  await openAndReplay();
  for (let i = 0; i < 3; i++) {
    await act(async () => { fake.player.onended?.(); });
    await flush();
  }
  await flush();
  expect(fake.player.play).toHaveBeenCalledTimes(3);
  expect(screen.getByText(/끝/)).toBeTruthy();
  expect(fake.sendEvent).not.toHaveBeenCalledWith("anon", "complete", "s1");
});

test("replay without audio moves to next segment instead of old choices", async () => {
  fake.getAudio.mockResolvedValue(undefined);
  fake.fetchSegmentAudio.mockRejectedValue(new ApiError(429, "tts_limit"));
  await openAndReplay();
  fireEvent.click(screen.getByText(/다음 ▶/));   // 0번 구간 2쪽
  fireEvent.click(screen.getByText(/다음 ▶/));   // 0번 구간 끝 → 다음 구간이어야 함
  await flush();
  expect(screen.getByText("2 / 3")).toBeTruthy();
  expect(screen.queryByText("bear")).toBeNull();  // 지난 구간 선택지가 나오면 안 됨
});
