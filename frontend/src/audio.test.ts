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
