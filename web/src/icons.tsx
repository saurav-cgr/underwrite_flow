/*
 * Icon set for the application shell.
 *
 * The paths are ported from designs/underwriteflow-ui/index.html so the React
 * UI and the design prototype draw the same shapes. Every icon is a stroked
 * outline; fill is never used.
 */

export type IconName =
  | "chevron"
  | "file"
  | "grid"
  | "inbox"
  | "log"
  | "plus"
  | "settings"
  | "shield";

interface IconProps {
  name: IconName;
  className?: string;
}

// Render the hidden sprite that every Icon reference resolves against.
export function IconSprite() {
  return (
    <svg aria-hidden="true" className="icon-sprite">
      <symbol id="i-grid" viewBox="0 0 24 24">
        <path d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z" />
      </symbol>
      <symbol id="i-plus" viewBox="0 0 24 24">
        <path d="M12 5v14M5 12h14" />
      </symbol>
      <symbol id="i-file" viewBox="0 0 24 24">
        <path
          d={
            "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"
            + "M14 2v6h6M8 13h8M8 17h5"
          }
        />
      </symbol>
      <symbol id="i-inbox" viewBox="0 0 24 24">
        <path d="M4 4h16l2 12v4H2v-4zM2 16h5l2 2h6l2-2h5" />
      </symbol>
      <symbol id="i-log" viewBox="0 0 24 24">
        <path d="M4 4h16v16H4zM8 8h8M8 12h8M8 16h5" />
      </symbol>
      <symbol id="i-settings" viewBox="0 0 24 24">
        <path
          d={
            "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"
            + "M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.83 2.83-.06-.06"
            + "a1.7 1.7 0 0 0-1.88-.34 1.7 1.7 0 0 0-1.03 1.56V21h-4v-.09"
            + "A1.7 1.7 0 0 0 9 19.36a1.7 1.7 0 0 0-1.88.34l-.06.06"
            + "-2.83-2.83.06-.06A1.7 1.7 0 0 0 4.63 15 1.7 1.7 0 0 0 "
            + "3.08 14H3v-4h.08A1.7 1.7 0 0 0 4.64 9a1.7 1.7 0 0 0-.34"
            + "-1.88l-.06-.06 2.83-2.83.06.06A1.7 1.7 0 0 0 9 4.63 "
            + "1.7 1.7 0 0 0 10 3.08V3h4v.08A1.7 1.7 0 0 0 15 4.64a1.7 "
            + "1.7 0 0 0 1.88-.34l.06-.06 2.83 2.83-.06.06A1.7 1.7 0 0 0 "
            + "19.37 9 1.7 1.7 0 0 0 20.92 10H21v4h-.08A1.7 1.7 0 0 0 "
            + "19.4 15z"
          }
        />
      </symbol>
      <symbol id="i-shield" viewBox="0 0 24 24">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10zm-3-10 2 2 4-4" />
      </symbol>
      <symbol id="i-chevron" viewBox="0 0 24 24">
        <path d="m9 18 6-6-6-6" />
      </symbol>
    </svg>
  );
}

// Render one sprite icon as a decorative inline SVG.
export function Icon({ name, className = "" }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      className={`icon ${className}`.trim()}
      focusable="false"
    >
      <use href={`#i-${name}`} />
    </svg>
  );
}
