import { useEffect, useRef } from "react";
import type { KeyboardEvent as ReactKeyboardEvent } from "react";

import { Button } from "./components";

// Ask for confirmation before one consequential, hard-to-reverse action.
export function ConfirmDialog({
  confirmLabel,
  detail,
  onCancel,
  onConfirm,
  title,
}: {
  confirmLabel: string;
  detail: string;
  onCancel: () => void;
  onConfirm: () => void;
  title: string;
}) {
  const dialogRef = useRef<HTMLDivElement>(null);

  // Move focus into the dialog and hand it back when the dialog closes.
  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    dialogRef.current?.focus();
    return () => opener?.focus?.();
  }, []);

  // Cancel on Escape, matching the native confirmation this replaces.
  useEffect(() => {
    function handleKey(event: KeyboardEvent) {
      if (event.key !== "Escape") return;
      event.preventDefault();
      onCancel();
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onCancel]);

  // Keep Tab focus between the two actions while the dialog is modal.
  function trapTab(event: ReactKeyboardEvent<HTMLDivElement>) {
    if (event.key !== "Tab") return;
    const actions = Array.from(
      event.currentTarget.querySelectorAll<HTMLElement>("button"),
    );
    if (actions.length === 0) return;
    const first = actions[0];
    const last = actions[actions.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  return (
    <div className="modal-overlay">
      <div
        aria-describedby="confirm-detail"
        aria-labelledby="confirm-title"
        aria-modal="true"
        className="modal"
        onKeyDown={trapTab}
        ref={dialogRef}
        role="dialog"
        tabIndex={-1}
      >
        <h2 id="confirm-title">{title}</h2>
        <p id="confirm-detail">{detail}</p>
        <div className="modal-actions">
          <Button onClick={onCancel} variant="quiet">
            Cancel
          </Button>
          <Button onClick={onConfirm} variant="danger">
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
