import { expect, test } from "vitest";
import { getGuideVoice, getRate, isCurrent, playToken, RATES, setGuideVoice, stepRate } from "./audio";

test("old token is not current after new token", () => {
  const first = playToken();
  expect(isCurrent(first)).toBe(true);
  const second = playToken();
  expect(isCurrent(first)).toBe(false);
  expect(isCurrent(second)).toBe(true);
});

test("rate steps up and down within the list", () => {
  expect(getRate()).toBe(1);  // 기본은 1배 (속도는 TTS 연출 지시로 맞춤)
  expect(stepRate(1, 1)).toBe(1.1);
  expect(stepRate(1, -1)).toBe(0.9);
  expect(stepRate(RATES[0], -1)).toBe(RATES[0]);
  expect(stepRate(RATES.at(-1)!, 1)).toBe(RATES.at(-1));
});

test("guide voice is remembered (memory when no localStorage)", () => {
  setGuideVoice("male");
  expect(getGuideVoice()).toBe("male");
  setGuideVoice("browser");
  expect(getGuideVoice()).toBe("browser");
});

test("story voice fades out near the end and stops a little early", async () => {
  const { END_FADE_START, END_STOP, endVolume } = await import("./audio");
  expect(endVolume(5, 1)).toBe(1);                         // 끝에서 먼 곳은 그대로
  expect(endVolume(END_FADE_START, 1)).toBe(1);            // 줄이기 시작
  const mid = endVolume((END_FADE_START + END_STOP) / 2, 1);
  expect(mid).toBeGreaterThan(0.3);
  expect(mid).toBeLessThan(0.7);                           // 중간쯤이면 절반 정도
  expect(endVolume(END_STOP, 1)).toBe(0);                  // 여기서 멈춤
  expect(endVolume(END_STOP, 0.5)).toBe(0);
  expect(endVolume(10, 0.5)).toBe(0.5);                    // 설정한 목소리 크기를 넘지 않음
});
