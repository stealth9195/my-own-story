import { expect, test } from "vitest";
import type { SegmentResponse, StoryKey } from "./api";
import { addSegment, choose, nextArgs, pageAt, pageStartTimes, segmentText, storyTitle } from "./story";

const story: StoryKey = { id: "s1", cards: ["duck", "kind", "birthday", "crown"], choice_count: 4,
                          voice: { provider: "gemini", model: "m", voice: "Kore" } };

function res(index: number, done = false): SegmentResponse {
  return { story, index, done, segment: { sig: `sig${index}`, segment: {
    type: index === 0 ? "intro" : "middle",
    pages: [{ text: "가나", scene: { background: "forest", time: "day", characters: [], objects: [] },
              mood: "calm", sfx: null }, { text: "다라마", scene: { background: "forest", time: "day",
              characters: [], objects: [] }, mood: "calm", sfx: null }],
    choices: [{ kind: "item", id: "fox", label: "여우" }],
  } } };
}

test("addSegment creates then appends", () => {
  const first = addSegment(null, res(0), 100);
  expect([first.story.id, first.segments.length, first.createdAt, first.done]).toEqual(["s1", 1, 100, false]);
  const second = addSegment(first, res(1, true), 200);
  expect([second.segments.length, second.createdAt, second.done]).toEqual([2, 100, true]);
  expect(first.segments.length).toBe(1);  // 원래 값은 바꾸지 않음
});

test("choose then nextArgs has same length history and chosen", () => {
  const s = choose(addSegment(null, res(0), 1), "fox");
  const args = nextArgs(s);
  expect(args.history.length).toBe(1);
  expect(args.chosen).toEqual(["fox"]);
  expect(args.story.id).toBe("s1");
});

test("pageStartTimes splits by char ratio", () => {
  expect(pageStartTimes(["가나", "가나다라"], 6)).toEqual([0, 2]);
});

test("pageAt picks last start not after time", () => {
  expect(pageAt(4.9, [0, 2, 5])).toBe(1);
  expect(pageAt(5, [0, 2, 5])).toBe(2);
  expect(pageAt(0, [0, 2, 5])).toBe(0);
});

test("storyTitle uses hero emoji and name", () => {
  expect(storyTitle(addSegment(null, res(0), 1))).toBe("🦆 오리 이야기");
});

test("segmentText joins pages", () => {
  expect(segmentText(res(0).segment.segment)).toBe("가나\n다라마");
});
