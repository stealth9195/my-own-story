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
  fireEvent.click(screen.getByText(/처음부터/));
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

test("moving to a shorter segment does not crash on the old page number", async () => {
  // 실제로 겪은 버그: 3쪽 구간을 다 듣고 2쪽 구간으로 넘어가면, 이전 페이지 번호(3쪽째)로 한 번 그리다가
  // 없는 페이지를 읽어 화면이 하얗게 멈췄다
  fake.getAudio.mockResolvedValue(new Blob(["mp3"]));
  const three: Segment = { ...seg("intro", ["bear", "owl", "moon"]),
    pages: [1, 2, 3].map((n) => ({ text: `intro ${n}`, scene, mood: "calm", sfx: null })) };
  const saved: SavedStory = { ...done, segments: [three, seg("middle", ["cake"]), seg("ending", [])]
    .map((segment, i) => ({ segment, sig: `sig${i}` })) };
  render(<Reading saved={saved} resume onUpdate={vi.fn()} onHome={vi.fn()} onNew={vi.fn()} />);
  await flush();
  fireEvent.click(screen.getByText(/처음부터/));
  await flush();
  fake.player.currentTime = 9;  // 0번 구간 3쪽째까지 들음 (음성 10초)
  await act(async () => {
    (fake.player.onloadedmetadata as (() => void) | null)?.();
    (fake.player.ontimeupdate as (() => void) | null)?.();
  });
  expect(screen.getByText("intro 3")).toBeTruthy();
  await act(async () => { fake.player.onended?.(); });  // 다음 구간(2쪽짜리)으로
  await flush();
  expect(screen.getByText("middle 1")).toBeTruthy();
});

test("done story offers to continue from the saved position", async () => {
  fake.getAudio.mockResolvedValue(new Blob(["mp3"]));
  localStorage.setItem("pos:s1", JSON.stringify({ view: 1, page: 1 }));  // 다시 듣다가 2번 구간 2쪽에서 멈춤
  render(<Reading saved={done} resume onUpdate={vi.fn()} onHome={vi.fn()} onNew={vi.fn()} />);
  await flush();
  fireEvent.click(screen.getByText(/이어 듣기/));
  await flush();
  await act(async () => { (fake.player.onloadedmetadata as (() => void) | null)?.(); });
  expect(screen.getByText("middle 2")).toBeTruthy();
  expect(fake.player.currentTime).toBeGreaterThan(0);  // 그 쪽 위치부터 재생
  localStorage.clear();
});

test("done story without saved position shows only start over", async () => {
  localStorage.clear();
  render(<Reading saved={done} resume onUpdate={vi.fn()} onHome={vi.fn()} onNew={vi.fn()} />);
  await flush();
  expect(screen.queryByText(/이어 듣기/)).toBeNull();
  expect(screen.getByText(/처음부터/)).toBeTruthy();
});

test("replay remembers the position and forgets it at the end", async () => {
  localStorage.clear();
  fake.getAudio.mockResolvedValue(new Blob(["mp3"]));
  render(<Reading saved={done} resume onUpdate={vi.fn()} onHome={vi.fn()} onNew={vi.fn()} />);
  await flush();
  fireEvent.click(screen.getByText(/처음부터/));
  await flush();
  await act(async () => { fake.player.onended?.(); });
  await flush();
  expect(JSON.parse(localStorage.getItem("pos:s1")!)).toEqual({ view: 1, page: 0 });
  for (let i = 0; i < 2; i++) { await act(async () => { fake.player.onended?.(); }); await flush(); }
  expect(localStorage.getItem("pos:s1")).toBeNull();
});
