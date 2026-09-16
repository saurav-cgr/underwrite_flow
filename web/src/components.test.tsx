// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Badge, Button, EmptyState } from "./components";
import "./test-setup";

// Verify the shared button stays keyboard operable and honours disabled state.
describe("shared button", () => {
  it("activates from the keyboard exactly once", async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(<Button onClick={onClick}>Submit documents</Button>);

    const button = screen.getByRole("button", {
      name: "Submit documents",
    });
    button.focus();
    await user.keyboard("{Enter}");

    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("refuses activation while disabled", async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(
      <Button disabled onClick={onClick}>
        Submit documents
      </Button>,
    );

    await user.click(
      screen.getByRole("button", { name: "Submit documents" }),
    );

    expect(onClick).not.toHaveBeenCalled();
  });
});

// Verify status and empty states stay readable without visual styling.
describe("shared status and empty state", () => {
  it("renders a status label as readable text", () => {
    render(<Badge tone="needs_information">Needs information</Badge>);

    expect(screen.getByText("Needs information")).toBeTruthy();
  });

  it("exposes the empty state heading and its detail", () => {
    render(
      <EmptyState
        title="No cases yet"
        detail="Nothing is waiting for review."
      />,
    );

    expect(
      screen.getByRole("heading", { name: "No cases yet" }),
    ).toBeTruthy();
    expect(
      screen.getByText("Nothing is waiting for review."),
    ).toBeTruthy();
  });
});
