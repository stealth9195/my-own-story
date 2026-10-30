// @vitest-environment jsdom
// 이야기 음성 끝 처리: 멈춘 직후 음량을 되돌리면 브라우저에 남은 소리가 원래 크기로 튀어 '콱' 소리가 날 수 있다
import { afterEach, expect, test, vi } from "vitest";
import { END_STOP, getVoiceVolume, speak, SPEAK_TIMEOUT_MS, watchEnd } from "./audio";

afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });

test("volume stays at 0 right after stopping near the end", () => {
  vi.useFakeTimers();
  vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => {});
  const audio = new Audio();
  Object.defineProperty(audio, "duration", { value: 10 });
  audio.currentTime = 10 - END_STOP + 0.01;
  const onEnd = vi.fn();
  watchEnd(audio, onEnd);
  vi.advanceTimersByTime(100);
  expect(onEnd).toHaveBeenCalledTimes(1);
  expect(audio.volume).toBe(0);  // 멈춘 뒤에도 0 (다음 재생 직전에 되돌린다)
  expect(getVoiceVolume()).toBeGreaterThan(0);
});

// 서버가 잠들어 /api/speak 가 응답하지 않으면 기다리다 멈추지 않고 브라우저 음성으로 넘어간다
test("speak falls back when the server hangs", async () => {
  vi.useFakeTimers();
  globalThis.fetch = vi.fn((_u: string | URL | Request, init?: RequestInit) => new Promise<Response>((_, reject) => {
    init?.signal?.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")));
  })) as typeof fetch;
  let done = false;
  speak("멈추지 않는 질문").then(() => { done = true; });
  await vi.advanceTimersByTimeAsync(SPEAK_TIMEOUT_MS + 100);
  expect(done).toBe(true);   // jsdom 에는 speechSynthesis 가 없어 바로 끝난다
  vi.useRealTimers();
});
