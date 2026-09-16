// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { ConfirmDialog } from "./confirm";
import "./test-setup";

// Render the dialog with synthetic handlers.
function renderDialog() {
  const onCancel = vi.fn();
  const onConfirm = vi.fn();
  render(
    <ConfirmDialog
      confirmLabel="Remove reference"
      detail="synthetic.pdf is no longer attached."
      onCancel={onCancel}
      onConfirm={onConfirm}
      title="Remove this reference?"
    />,
  );
  return { onCancel, onConfirm };
}

// Verify the dialog is labelled, modal, and keyboard operable.
describe("confirm dialog", () => {
  it("exposes a labelled modal dialog", () => {
    renderDialog();

    const dialog = screen.getByRole("dialog");
    expect(dialog.getAttribute("aria-modal")).toBe("true");
    expect(dialog.getAttribute("aria-labelledby")).toBe("confirm-title");
    expect(dialog.getAttribute("aria-describedby")).toBe("confirm-detail");
    expect(
      screen.getByRole("heading", { name: "Remove this reference?" }),
    ).toBeTruthy();
    expect(
      screen.getByText("synthetic.pdf is no longer attached."),
    ).toBeTruthy();
  });

  it("moves focus into the dialog so it is keyboard reachable", () => {
    renderDialog();

    expect(document.activeElement).toBe(screen.getByRole("dialog"));
  });

  it("reports a confirmed action", async () => {
    const { onConfirm } = renderDialog();
    const user = userEvent.setup();

    await user.click(
      screen.getByRole("button", { name: "Remove reference" }),
    );

    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("cancels on Escape", async () => {
    const { onCancel } = renderDialog();
    const user = userEvent.setup();

    await user.keyboard("{Escape}");

    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("cycles Tab focus between the two actions", async () => {
    renderDialog();
    const user = userEvent.setup();

    await user.tab();
    expect(document.activeElement).toBe(
      screen.getByRole("button", { name: "Cancel" }),
    );
    await user.tab();
    expect(document.activeElement).toBe(
      screen.getByRole("button", { name: "Remove reference" }),
    );
    await user.tab();
    expect(document.activeElement).toBe(
      screen.getByRole("button", { name: "Cancel" }),
    );
  });

  it("returns focus to the control that opened it", async () => {
    // Drive the dialog the way a screen does: open from a trigger, then close.
    function Harness() {
      const [open, setOpen] = useState(false);
      return (
        <>
          <button onClick={() => setOpen(true)} type="button">
            Remove
          </button>
          {open ? (
            <ConfirmDialog
              confirmLabel="Remove reference"
              detail="synthetic.pdf is no longer attached."
              onCancel={() => setOpen(false)}
              onConfirm={() => setOpen(false)}
              title="Remove this reference?"
            />
          ) : null}
        </>
      );
    }
    render(<Harness />);
    const user = userEvent.setup();
    const trigger = screen.getByRole("button", { name: "Remove" });

    await user.click(trigger);
    expect(screen.getByRole("dialog")).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(screen.queryByRole("dialog")).toBeNull();
    expect(document.activeElement).toBe(trigger);
  });
});
