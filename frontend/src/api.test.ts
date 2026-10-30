import { afterEach, describe, expect, test, vi } from "vitest";
import { ApiError, AUDIO_TIMEOUT_MS, fetchSegmentAudio, getDemoVoices, getStartOptions, nextSegment, sendEvent, startStory, STORY_TIMEOUT_MS, WAKE_TIMEOUT_MS, wakeServer } from "./api";
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
  test("startStory posts anon_id, cards, choice_count, voice", async () => {
    mockFetch(() => json({ story, index: 0, segment: signed, done: false }));
    const res = await startStory("anon", story.cards);
    expect(calls[0].url).toBe("/api/stories");
    // 이야기 목소리를 고르지 않았으면 voice: null (서버가 무작위)
    expect(JSON.parse(String(calls[0].init?.body))).toEqual({ anon_id: "anon", cards: story.cards, choice_count: 4, voice: null });
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

describe("timeouts", () => {
  // 응답이 오지 않는 fetch: abort 신호가 오면 그때 실패한다
  function hangingFetch() {
    globalThis.fetch = vi.fn((_url: string | URL | Request, init?: RequestInit) =>
      new Promise<Response>((_, reject) => {
        init?.signal?.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")));
      })) as typeof fetch;
  }

  test("hung story request becomes network error", async () => {
    vi.useFakeTimers();
    hangingFetch();
    const p = startStory("anon", story.cards).catch((e) => e);
    await vi.advanceTimersByTimeAsync(STORY_TIMEOUT_MS + 1);
    const err = await p;
    expect(err).toBeInstanceOf(ApiError);
    expect(err.code).toBe("network");
    vi.useRealTimers();
  });

  test("hung audio request becomes network error", async () => {
    vi.useFakeTimers();
    hangingFetch();
    const p = fetchSegmentAudio(story, 0, signed).catch((e) => e);
    await vi.advanceTimersByTimeAsync(AUDIO_TIMEOUT_MS + 1);
    expect((await p).code).toBe("network");
    vi.useRealTimers();
  });
});

// Render 무료 서버는 15분 쉬면 잠들고 깨는 데 약 1분 걸린다
describe("wake server", () => {
  test("start options wait for a sleeping server", async () => {
    vi.useFakeTimers();
    let answer: (r: Response) => void = () => {};
    globalThis.fetch = vi.fn(() => new Promise<Response>((ok) => { answer = ok; })) as typeof fetch;
    const p = getStartOptions();
    await vi.advanceTimersByTimeAsync(50_000);   // 예전 20초 제한이면 여기서 실패
    answer(new Response(JSON.stringify({ steps: [] })));
    await expect(p).resolves.toEqual({ steps: [] });
    expect(WAKE_TIMEOUT_MS).toBeGreaterThanOrEqual(60_000);
    vi.useRealTimers();
  });

  test("wakeServer ignores failures", async () => {
    globalThis.fetch = vi.fn(async () => { throw new TypeError("offline"); }) as typeof fetch;
    expect(() => wakeServer()).not.toThrow();
    await Promise.resolve();
    expect(globalThis.fetch).toHaveBeenCalledWith(expect.stringContaining("/api/start-options"), expect.anything());
  });
});

describe("demo voices", () => {
  test("lists server demo voices", async () => {
    globalThis.fetch = vi.fn(async () => new Response(JSON.stringify([{ id: "eleven1", name: "경상도 사투리" }]))) as typeof fetch;
    expect(await getDemoVoices()).toEqual([["eleven1", "경상도 사투리"]]);
  });

  test("empty when server fails", async () => {
    globalThis.fetch = vi.fn(async () => { throw new TypeError("offline"); }) as typeof fetch;
    expect(await getDemoVoices()).toEqual([]);
  });
});
