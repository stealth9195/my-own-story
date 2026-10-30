// @vitest-environment jsdom
// 효과음은 페이지가 바뀌고 2초 뒤에, 그 사이 다음 페이지로 넘어가면 앞 효과음은 취소
import { afterEach, expect, test, vi } from "vitest";
import { playSfx, sfxPlayer } from "./sound";

afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });

test("sound effect plays after 2 seconds", () => {
  vi.useFakeTimers();
  const play = vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue(undefined);
  playSfx("bell");
  vi.advanceTimersByTime(1900);
  expect(play).not.toHaveBeenCalled();
  vi.advanceTimersByTime(200);
  expect(play).toHaveBeenCalledTimes(1);
  expect(sfxPlayer?.src).toContain("/sound/bell.mp3");
});

test("next page cancels the waiting sound effect", () => {
  vi.useFakeTimers();
  const play = vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue(undefined);
  playSfx("bell");
  vi.advanceTimersByTime(1000);
  playSfx(null);  // 다음 페이지는 효과음 없음
  vi.advanceTimersByTime(3000);
  expect(play).not.toHaveBeenCalled();
});
