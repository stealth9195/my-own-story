// @vitest-environment jsdom
// 그림 파일이 없으면(불러오기 실패) 이모지로 바뀌는지
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test } from "vitest";
import Picture from "./Picture";

afterEach(cleanup);

test("shows webp image by id", () => {
  const { container } = render(<Picture id="bear" size={80} />);
  expect(container.querySelector("img")?.getAttribute("src")).toBe("/img/bear.webp");
});

test("falls back to emoji on error", () => {
  const { container } = render(<Picture id="bear" size={80} />);
  fireEvent.error(container.querySelector("img")!);
  expect(screen.getByText("🐻")).toBeTruthy();
  expect(container.querySelector("img")).toBeNull();
});
