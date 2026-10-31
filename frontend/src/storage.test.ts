import "fake-indexeddb/auto";
import { clear } from "idb-keyval";
import { beforeEach, expect, test } from "vitest";
import type { StoryKey } from "./api";
import { deleteStory, getAnonId, getAudio, getStory, listStories, pruneAudio, saveAudio, saveStory } from "./storage";
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

test("delete removes the story and its audio only", async () => {
  await saveStory(saved("a", 1));
  await saveStory(saved("ab", 2));  // id 가 'a' 로 시작해도 지우지 않는다
  await saveAudio("a", 0, new Blob([new Uint8Array([1])]));
  await saveAudio("a", 3, new Blob([new Uint8Array([2])]));
  await saveAudio("ab", 0, new Blob([new Uint8Array([3])]));
  await deleteStory("a");
  expect(await getStory("a")).toBeUndefined();
  expect(await getAudio("a", 0)).toBeUndefined();
  expect(await getAudio("a", 3)).toBeUndefined();
  expect(await getStory("ab")).toBeDefined();
  expect(await getAudio("ab", 0)).toBeDefined();
});

test("favorite is saved with the story", async () => {
  await saveStory({ ...saved("a", 1), favorite: true });
  expect((await getStory("a"))?.favorite).toBe(true);
});

test("anon id is stable", () => {
  expect(getAnonId()).toBe(getAnonId());
  expect(getAnonId().length).toBeGreaterThan(8);
});
