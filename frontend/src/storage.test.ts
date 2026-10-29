import "fake-indexeddb/auto";
import { clear } from "idb-keyval";
import { beforeEach, expect, test } from "vitest";
import type { StoryKey } from "./api";
import { getAnonId, getAudio, getStory, listStories, pruneAudio, saveAudio, saveStory } from "./storage";
import type { SavedStory } from "./storage";

function saved(id: string, createdAt: number): SavedStory {
  const story: StoryKey = { id, cards: ["rabbit"], choice_count: 4, voice: { provider: "browser" } };
  return { story, segments: [], chosen: [], createdAt, done: false };
}

beforeEach(async () => {
  await clear();
});

test("save and get story", async () => {
  await saveStory(saved("a", 1));
  expect((await getStory("a"))?.story.id).toBe("a");
  expect(await getStory("nope")).toBeUndefined();
});

test("list newest first", async () => {
  for (const [id, t] of [["a", 1], ["c", 3], ["b", 2]] as const) await saveStory(saved(id, t));
  expect((await listStories()).map((s) => s.createdAt)).toEqual([3, 2, 1]);
});

test("audio roundtrip", async () => {
  await saveAudio("a", 0, new Blob([new Uint8Array([1, 2, 3])], { type: "audio/mpeg" }));
  expect((await getAudio("a", 0))?.size).toBe(3);
  expect(await getAudio("a", 1)).toBeUndefined();
});

test("prune keeps latest 20 audios", async () => {
  for (let i = 0; i < 22; i++) {
    await saveStory(saved(`s${i}`, i));
    await saveAudio(`s${i}`, 0, new Blob([new Uint8Array([i])]));
  }
  await pruneAudio(20);
  expect(await getAudio("s0", 0)).toBeUndefined();
  expect(await getAudio("s1", 0)).toBeUndefined();
  expect(await getAudio("s2", 0)).toBeDefined();
  expect((await listStories()).length).toBe(22);
});

test("anon id is stable", () => {
  expect(getAnonId()).toBe(getAnonId());
  expect(getAnonId().length).toBeGreaterThan(8);
});
