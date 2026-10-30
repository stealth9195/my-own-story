// @vitest-environment jsdom
// 이야기 음성 끝 처리: 멈춘 직후 음량을 되돌리면 브라우저에 남은 소리가 원래 크기로 튀어 '콱' 소리가 날 수 있다
import { afterEach, expect, test, vi } from "vitest";
import { END_STOP, getVoiceVolume, watchEnd } from "./audio";

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
