// IndexedDB 를 쓸 수 없는 환경(사파리 비공개 모드 등): 저장만 안 되고 오류는 나지 않아야 한다
// (fake-indexeddb 를 불러오지 않으므로 이 파일에서는 indexedDB 가 없다)
import { expect, test } from "vitest";
import type { StoryKey } from "./api";
import { getAudio, getStory, listStories, pruneAudio, saveAudio, saveStory } from "./storage";

const story: StoryKey = { id: "x", cards: ["rabbit"], choice_count: 4, voice: { provider: "browser" } };

test("storage errors do not throw", async () => {
  expect(globalThis.indexedDB).toBeUndefined();
  await expect(saveStory({ story, segments: [], chosen: [], createdAt: 1, done: false })).resolves.toBeUndefined();
  await expect(saveAudio("x", 0, new Blob([]))).resolves.toBeUndefined();
  expect(await getStory("x")).toBeUndefined();
  expect(await getAudio("x", 0)).toBeUndefined();
  expect(await listStories()).toEqual([]);
  await expect(pruneAudio()).resolves.toBeUndefined();
});
