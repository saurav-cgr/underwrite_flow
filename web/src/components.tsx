import type { ReactNode } from "react";
import type { Role, Screen } from "./types";

interface ButtonProps {
  children: ReactNode;
  onClick?: () => void;
  type?: "button" | "submit";
  variant?: "primary" | "secondary" | "quiet" | "danger";
  disabled?: boolean;
}

// Render a consistent native button with visible focus and press states.
export function Button({
  children,
  onClick,
  type = "button",
  variant = "primary",
  disabled = false,
}: ButtonProps) {
  return (
    <button
      className={`button button-${variant}`}
      disabled={disabled}
      onClick={onClick}
      type={type}
    >
      {children}
    </button>
  );
}

// Render a compact status label that does not rely on color alone.
export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

// Render the product mark as a scalable decorative SVG.
export function BrandMark() {
  return (
    <span className="brand-mark" aria-hidden="true">
      <svg viewBox="0 0 32 32" role="img">
        <path
          d={
            "M16 3 27 8v8c0 6.7-4.2 10.8-11 13C9.2 26.8 "
            + "5 22.7 5 16V8l11-5Z"
          }
        />
        <path d="m10 16 4 4 8-9" />
      </svg>
    </span>
  );
}

// Render the persistent application frame and role-aware navigation.
export function AppShell({
  role,
  screen,
  onNavigate,
  onSignOut,
  children,
}: {
  role: Role;
  screen: Screen;
  onNavigate: (screen: Screen) => void;
  onSignOut: () => void;
  children: ReactNode;
}) {
  const links: { screen: Screen; label: string }[] =
    role === "Applicant"
      ? [
          { screen: "dashboard", label: "Overview" },
          { screen: "products", label: "New application" },
          { screen: "tracking", label: "My cases" },
        ]
      : role === "Underwriter"
        ? [{ screen: "queue", label: "Review queue" }]
        : [
            { screen: "admin", label: "Audit workspace" },
            { screen: "queue", label: "All queues" },
          ];

  // Return to the role's primary screen from the brand link.
  function goHome() {
    onNavigate(
      role === "Applicant"
        ? "dashboard"
        : role === "Underwriter"
          ? "queue"
          : "admin",
    );
  }

  return (
    <div className="app-frame">
      <header className="topbar">
        <button className="brand" onClick={goHome} type="button">
          <BrandMark />
          <span>
            Underwrite<span className="brand-accent">Flow</span>
          </span>
        </button>
        <div className="topbar-actions">
          <span className="role-label">{role} workspace</span>
          <button className="signout" onClick={onSignOut} type="button">
            Sign out
          </button>
        </div>
      </header>
      <div className="workspace">
        <aside className="sidebar" aria-label="Workspace navigation">
          <p className="eyebrow">Workspace</p>
          <nav>
            {links.map((link) => (
              <button
                aria-current={screen === link.screen ? "page" : undefined}
                className={
                  `nav-link ${screen === link.screen ? "nav-link-active" : ""}`
                }
                key={link.screen}
                onClick={() => onNavigate(link.screen)}
                type="button"
              >
                <span className="nav-rule" aria-hidden="true" />
                {link.label}
              </button>
            ))}
          </nav>
          <div className="sidebar-note">
            <p className="eyebrow">Human governance</p>
            <p>
              Recommendations organize work. An underwriter confirms every
              final route.
            </p>
          </div>
        </aside>
        <main className="content" id="top">
          {children}
        </main>
      </div>
    </div>
  );
}

// Render a reusable page heading with optional action content.
export function PageHeading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="lede">{description}</p>
      </div>
      {action ? <div className="heading-action">{action}</div> : null}
    </div>
  );
}

// Render a bordered content panel with an optional title row.
export function Panel({
  title,
  children,
  className = "",
}: {
  title?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel ${className}`}>
      {title ? <h2 className="panel-title">{title}</h2> : null}
      {children}
    </section>
  );
}

// Render a simple progress trail for the applicant journey.
export function Journey({ current }: { current: number }) {
  const steps = ["Application", "Documents", "Review", "Complete"];
  return (
    <ol className="journey" aria-label="Application progress">
      {steps.map((step, index) => (
        <li className={index <= current ? "journey-done" : ""} key={step}>
          <span>{index + 1}</span>
          <strong>{step}</strong>
        </li>
      ))}
    </ol>
  );
}

// Render an accessible error summary linked to invalid fields.
export function ErrorSummary({ errors }: { errors: Record<string, string> }) {
  const entries = Object.entries(errors);
  if (entries.length === 0) return null;
  return (
    <div className="error-summary" role="alert" tabIndex={-1}>
      <strong>There is a problem</strong>
      <ul>
        {entries.map(([key, message]) => (
          <li key={key}>
            <a href={`#${key}`}>{message}</a>
          </li>
        ))}
      </ul>
    </div>
  );
}

// Render a neutral empty state when a queue or audit lookup has no result.
export function EmptyState({
  title,
  detail,
}: {
  title: string;
  detail: string;
}) {
  return (
    <div className="empty-state">
      <span className="empty-line" aria-hidden="true" />
      <h2>{title}</h2>
      <p>{detail}</p>
    </div>
  );
}
