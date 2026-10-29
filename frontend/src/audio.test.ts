import { expect, test } from "vitest";
import { isCurrent, playToken } from "./audio";

test("old token is not current after new token", () => {
  const first = playToken();
  expect(isCurrent(first)).toBe(true);
  const second = playToken();
  expect(isCurrent(first)).toBe(false);
  expect(isCurrent(second)).toBe(true);
});
