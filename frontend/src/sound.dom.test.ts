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

test("music volume changes smoothly when the story voice starts", async () => {
  vi.useFakeTimers();
  const { bgmPlayer, duckBgm } = await import("./sound");
  bgmPlayer!.volume = 0.4;
  duckBgm(true);
  expect(bgmPlayer!.volume).toBeGreaterThan(0.3);   // 바로 뚝 떨어지지 않고
  vi.advanceTimersByTime(500);
  expect(bgmPlayer!.volume).toBeCloseTo(0.15, 2);   // 0.4초쯤 뒤 목표 크기
  duckBgm(false);
  vi.advanceTimersByTime(500);
  expect(bgmPlayer!.volume).toBeCloseTo(0.4, 2);
});
