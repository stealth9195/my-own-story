import { expect, test } from "vitest";
import { isMuted, pickBgm, setMuted } from "./sound";
import type { Bgm } from "./sound";

const calm: Bgm = { id: "calm_loop", name: "평화", mood: "calm" };
const mystery: Bgm = { id: "mystery_loop", name: "신비", mood: "mystery" };
const warm: Bgm = { id: "warm_loop", name: "따뜻", mood: "warm" };
const ending: Bgm = { id: "ending_loop", name: "결말", mood: "ending" };
const first = () => 0;

test("pickBgm same mood", () => {
  expect(pickBgm([calm, mystery], "mystery", false, first)).toBe("mystery_loop");
});

test("pickBgm falls back to calm", () => {
  expect(pickBgm([calm, mystery], "tense", false, first)).toBe("calm_loop");
});

test("pickBgm ending prefers ending then warm then calm", () => {
  expect(pickBgm([calm, warm, ending], "exciting", true, first)).toBe("ending_loop");
  expect(pickBgm([calm, warm], "exciting", true, first)).toBe("warm_loop");
  expect(pickBgm([calm, mystery], "mystery", true, first)).toBe("calm_loop");
});

test("pickBgm random among same mood", () => {
  const calm2: Bgm = { id: "calm_2", name: "평화2", mood: "calm" };
  expect(pickBgm([calm, calm2], "calm", false, () => 0)).toBe("calm_loop");
  expect(pickBgm([calm, calm2], "calm", false, () => 0.99)).toBe("calm_2");
});

test("pickBgm none", () => {
  expect(pickBgm([], "calm", false, first)).toBeNull();
});

test("mute persists", () => {
  // 테스트 환경(node)에는 localStorage 가 없다 → 오류 없이 이번 실행 동안 기억
  setMuted(true);
  expect(isMuted()).toBe(true);
  setMuted(false);
  expect(isMuted()).toBe(false);
});
