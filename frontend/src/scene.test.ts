import { expect, test } from "vitest";
import { actorSlots, stateMark, timeFilter } from "./scene";

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
