import { expect, test } from "vitest";
import { actorSlots, arrangeActors, placeObjects, stateMark, timeFilter } from "./scene";

test("actorSlots spreads evenly", () => {
  expect(actorSlots(1)[0].left).toBe(50);
  const lefts = actorSlots(3).map((s) => s.left);
  expect(lefts).toEqual([...lefts].sort((a, b) => a - b));
  for (const left of actorSlots(4).map((s) => s.left)) {
    expect(left).toBeGreaterThanOrEqual(10);
    expect(left).toBeLessThanOrEqual(90);
  }
});

test("actorSlots keeps at most 4", () => {
  expect(actorSlots(6)).toHaveLength(4);
  expect(actorSlots(0)).toHaveLength(0);
});

test("stateMark known and idle", () => {
  expect(stateMark("sleeping")).toBe("💤");
  expect(stateMark("idle")).toBeNull();
  expect(stateMark("dancing")).toBeNull();
});

test("timeFilter night darker", () => {
  expect(timeFilter("night")).toContain("brightness");
  expect(timeFilter("day")).toBe("none");
  expect(timeFilter("unknown")).toBe("none");
});

// facing: 그림 속 캐릭터가 보는 방향. 결과는 왼쪽→오른쪽 순서
const ch = (id: string, facing: string) => ({ id, state: "idle", facing });

test("arrangeActors puts right-facing on left and left-facing on right", () => {
  const out = arrangeActors([ch("fox", "left"), ch("bear", "right")], []);
  expect(out.map((a) => a.id)).toEqual(["bear", "fox"]);
  expect(out.map((a) => a.flip)).toEqual([false, false]);
});

test("arrangeActors flips one of two same-direction characters", () => {
  const out = arrangeActors([ch("fox", "left"), ch("owl", "left")], []);
  expect(out.map((a) => a.flip)).toEqual([true, false]);  // 왼쪽 자리는 오른쪽을 보도록 뒤집음
  expect(out.map((a) => a.looks)).toEqual(["right", "left"]);
});

test("arrangeActors never flips front or a single centered character", () => {
  expect(arrangeActors([ch("fox", "left")], [])[0].flip).toBe(false);
  const out = arrangeActors([ch("monkey", "front"), ch("owl", "left"), ch("bear", "right")], []);
  expect(out.map((a) => a.id)).toEqual(["bear", "monkey", "owl"]);
  expect(out.every((a) => !a.flip)).toBe(true);
});

test("arrangeActors treats unknown facing as front", () => {
  const out = arrangeActors([ch("boy", ""), ch("girl", "")], []);
  expect(out.every((a) => !a.flip)).toBe(true);
});

test("arrangeActors puts objects after characters, max 4", () => {
  const out = arrangeActors([ch("bear", "right")], ["apple", "key", "star", "moon"]);
  expect(out.map((a) => a.id)).toEqual(["bear", "apple", "key", "star"]);
  expect(out[1]).toMatchObject({ object: true, flip: false });
});

// 사물 위치: head·hand 는 캐릭터에게 붙이고, sky 는 하늘, 나머지는 바닥
const PLACES: Record<string, string> = { crown: "head", flower_crown: "head", magic_wand: "hand", lantern: "hand", moon: "sky" };
const placeOf = (id: string) => PLACES[id];

test("placeObjects puts crown on the first character's head", () => {
  const out = placeObjects(["princess", "fox"], ["crown", "cake"], placeOf);
  expect(out.worn).toEqual([{ id: "crown", on: "princess", place: "head" }]);
  expect(out.ground).toEqual(["cake"]);
});

test("placeObjects gives each character at most one head and one hand item", () => {
  const out = placeObjects(["bear"], ["crown", "flower_crown", "magic_wand"], placeOf);
  expect(out.worn).toEqual([{ id: "crown", on: "bear", place: "head" }, { id: "magic_wand", on: "bear", place: "hand" }]);
  expect(out.ground).toEqual(["flower_crown"]);
});

test("placeObjects spreads items over characters in order", () => {
  const out = placeObjects(["bear", "fox"], ["crown", "flower_crown"], placeOf);
  expect(out.worn.map((w) => w.on)).toEqual(["bear", "fox"]);
});

test("placeObjects without characters keeps items on the ground, sky goes up", () => {
  const out = placeObjects([], ["crown", "moon", "cake"], placeOf);
  expect(out.ground).toEqual(["crown", "cake"]);
  expect(out.sky).toEqual(["moon"]);
});
