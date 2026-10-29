import { expect, test } from "vitest";
import { emojiOf, nameOf } from "./catalog";

test("emojiOf known and unknown", () => {
  expect(emojiOf("rabbit")).not.toBe("❓");
  expect(emojiOf("nope")).toBe("❓");
  expect(nameOf("rabbit")).toBe("토끼");
});
