import { afterEach, describe, expect, test, vi } from "vitest";
import { ApiError, fetchSegmentAudio, nextSegment, sendEvent, startStory } from "./api";
import type { SignedSegment, StoryKey } from "./api";

const calls: { url: string; init?: RequestInit }[] = [];

function mockFetch(respond: () => Response | Promise<Response>) {
  calls.length = 0;
  globalThis.fetch = vi.fn(async (url: string | URL | Request, init?: RequestInit) => {
    calls.push({ url: String(url), init });
    return respond();
  }) as typeof fetch;
}

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

const story: StoryKey = {
  id: "s1", cards: ["rabbit", "kind", "forest", "rose"], choice_count: 4,
  voice: { provider: "gemini", model: "m", voice: "Kore" },
};
const signed: SignedSegment = { segment: { type: "intro", pages: [], choices: [] }, sig: "abc" };

afterEach(() => vi.restoreAllMocks());

describe("api", () => {
  test("startStory posts anon_id, cards, choice_count", async () => {
    mockFetch(() => json({ story, index: 0, segment: signed, done: false }));
    const res = await startStory("anon", story.cards);
    expect(calls[0].url).toBe("/api/stories");
    expect(JSON.parse(String(calls[0].init?.body))).toEqual({ anon_id: "anon", cards: story.cards, choice_count: 4 });
    expect(res.index).toBe(0);
  });

  test("nextSegment posts story, history, chosen", async () => {
    mockFetch(() => json({ story, index: 1, segment: signed, done: false }));
    await nextSegment("anon", story, [signed], ["dragon"]);
    expect(calls[0].url).toBe("/api/stories/next");
    expect(JSON.parse(String(calls[0].init?.body))).toEqual({ anon_id: "anon", story, history: [signed], chosen: ["dragon"] });
  });

  test("error body code becomes ApiError", async () => {
    mockFetch(() => json({ detail: { code: "user_limit" } }, 429));
    const err = await startStory("anon", story.cards).catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect([err.status, err.code]).toEqual([429, "user_limit"]);
  });

  test("network failure becomes ApiError network", async () => {
    globalThis.fetch = vi.fn(async () => { throw new TypeError("Failed to fetch"); }) as typeof fetch;
    const err = await startStory("anon", story.cards).catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.code).toBe("network");
  });

  test("fetchSegmentAudio returns blob", async () => {
    mockFetch(() => new Response(new Uint8Array([0xff, 0xfb]), { headers: { "Content-Type": "audio/mpeg" } }));
    const blob = await fetchSegmentAudio(story, 0, signed);
    expect(calls[0].url).toBe("/api/tts");
    expect(blob.size).toBe(2);
  });

  test("sendEvent swallows errors", async () => {
    globalThis.fetch = vi.fn(async () => { throw new TypeError("offline"); }) as typeof fetch;
    expect(() => sendEvent("anon", "complete", "s1")).not.toThrow();
    await new Promise((r) => setTimeout(r, 0));
  });
});
