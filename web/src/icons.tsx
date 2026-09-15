/*
 * Icon set for the application shell.
 *
 * The paths are ported from designs/underwriteflow-ui/index.html so the React
 * UI and the design prototype draw the same shapes. Every icon is a stroked
 * outline; fill is never used.
 */

export type IconName =
  | "alert"
  | "arrow"
  | "car"
  | "check"
  | "chevron"
  | "clock"
  | "file"
  | "filter"
  | "grid"
  | "health"
  | "heart"
  | "inbox"
  | "log"
  | "plus"
  | "search"
  | "settings"
  | "shield"
  | "upload"
  | "user";

const FAMILY_ICONS: Record<string, IconName> = {
  health: "health",
  life: "heart",
  motor: "car",
};

// Describe the product mark for a configured product family.
export function familyMark(family: string): {
  icon: IconName;
  className: string;
} {
  const key = family.toLowerCase();
  if (key in FAMILY_ICONS) return { icon: FAMILY_ICONS[key], className: key };
  return { icon: "file", className: "other" };
}

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
      <symbol id="i-alert" viewBox="0 0 24 24">
        <path
          d={
            "M10.3 3.7 2.2 18a2 2 0 0 0 1.8 3h16a2 2 0 0 0 1.8-3"
            + "L13.7 3.7a2 2 0 0 0-3.4 0zM12 9v4M12 17h.01"
          }
        />
      </symbol>
      <symbol id="i-arrow" viewBox="0 0 24 24">
        <path d="M5 12h14M13 6l6 6-6 6" />
      </symbol>
      <symbol id="i-car" viewBox="0 0 24 24">
        <path
          d={
            "m5 17-2-2 1.5-6h15L21 15l-2 2"
            + "M7 9l2-4h6l2 4M5 17v2M19 17v2M6 14h.01M18 14h.01M7 17h10"
          }
        />
      </symbol>
      <symbol id="i-check" viewBox="0 0 24 24">
        <path d="m5 12 4 4L19 6" />
      </symbol>
      <symbol id="i-clock" viewBox="0 0 24 24">
        <path d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 7v5l3 2" />
      </symbol>
      <symbol id="i-health" viewBox="0 0 24 24">
        <path
          d={
            "M12 21C7 18 4 14 4 9a4 4 0 0 1 7-2.6L12 8l1-1.6A4 4 0 0 1"
            + " 20 9c0 5-3 9-8 12zM8 12h2l1-2 2 4 1-2h2"
          }
        />
      </symbol>
      <symbol id="i-heart" viewBox="0 0 24 24">
        <path
          d={
            "M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0"
            + "-7.8 7.8l1.1 1.1L12 21l7.8-7.5 1.1-1.1a5.5 5.5 0 0 0-.1-7.8z"
          }
        />
      </symbol>
      <symbol id="i-upload" viewBox="0 0 24 24">
        <path d="M12 16V4M7 9l5-5 5 5M4 20h16" />
      </symbol>
      <symbol id="i-user" viewBox="0 0 24 24">
        <path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21a8 8 0 0 1 16 0" />
      </symbol>
      <symbol id="i-search" viewBox="0 0 24 24">
        <path d="M18 11a7 7 0 1 0-14 0 7 7 0 0 0 14 0zm-2 6 4 4" />
      </symbol>
      <symbol id="i-filter" viewBox="0 0 24 24">
        <path d="M4 5h16M7 12h10M10 19h4" />
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
