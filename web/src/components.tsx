import type { ReactNode } from "react";
import { useEffect, useRef } from "react";
import { Icon, IconSprite } from "./icons";
import type { IconName } from "./icons";
import { homeScreenForRole, identityInitials } from "./ui-state";
import type { Role, Screen, Session } from "./types";

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
      className={`btn btn-${variant}`}
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
  return <span className={`status status-${tone}`}>{children}</span>;
}

// Render the product mark as a scalable decorative SVG.
export function BrandMark() {
  return (
    <span className="brand-mark" aria-hidden="true">
      <Icon name="shield" />
    </span>
  );
}

interface ShellLink {
  screen: Screen;
  label: string;
  icon: IconName;
}

// Describe the navigation each role may reach from the shell.
function shellLinks(role: Role): ShellLink[] {
  if (role === "Applicant") {
    return [
      { screen: "dashboard", label: "Overview", icon: "grid" },
      { screen: "journey", label: "New application", icon: "plus" },
      { screen: "tracking", label: "My cases", icon: "file" },
    ];
  }
  if (role === "Underwriter") {
    return [{ screen: "queue", label: "Review queue", icon: "inbox" }];
  }
  return [
    { screen: "admin", label: "Audit workspace", icon: "log" },
    {
      screen: "product_config",
      label: "Product configuration",
      icon: "settings",
    },
    { screen: "queue", label: "All queues", icon: "inbox" },
  ];
}

// Render the persistent application frame and role-aware navigation.
export function AppShell({
  session,
  screen,
  onNavigate,
  onSignOut,
  children,
}: {
  session: Session;
  screen: Screen;
  onNavigate: (screen: Screen) => void;
  onSignOut: () => void;
  children: ReactNode;
}) {
  const links = shellLinks(session.role);

  return (
    <div className="app-frame">
      <IconSprite />
      <aside aria-label="Workspace navigation" className="sidebar">
        <button
          aria-label="UnderwriteFlow home"
          className="brand"
          onClick={() => onNavigate(homeScreenForRole(session.role))}
          type="button"
        >
          <BrandMark />
          <span>
            <b>Underwrite</b>Flow
          </span>
        </button>
        <nav className="nav-list">
          {links.map((link) => (
            <button
              aria-current={screen === link.screen ? "page" : undefined}
              aria-label={link.label}
              className="nav-link"
              key={link.screen}
              onClick={() => onNavigate(link.screen)}
              type="button"
            >
              <Icon name={link.icon} />
              <span>{link.label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-note">
          <span className="eyebrow">Human governance</span>
          <p>
            Recommendations organize work. An underwriter confirms every
            final route.
          </p>
        </div>
        <div className="profile-switch">
          <span aria-hidden="true" className="avatar">
            {identityInitials(session.email)}
          </span>
          <span>
            <b>{session.email}</b>
            <small>{session.role}</small>
          </span>
        </div>
        <button
          className="btn btn-quiet signout"
          onClick={onSignOut}
          type="button"
        >
          Sign out
        </button>
      </aside>
      <main className="main-content" id="top">
        <section className="screen">{children}</section>
      </main>
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
    <section className={`card ${className}`}>
      {title ? <h2 className="card-title">{title}</h2> : null}
      {children}
    </section>
  );
}

// Return the stepper state class for one step index.
function stepState(index: number, current: number): string {
  if (index < current) return "done";
  if (index === current) return "active";
  return "";
}

// Render a simple progress trail for the applicant journey.
export function Journey({ current }: { current: number }) {
  const steps = ["Application", "Documents", "Review", "Complete"];
  return (
    <ol className="stepper" aria-label="Application progress">
      {steps.map((step, index) => (
        <li className={stepState(index, current)} key={step}>
          <span>{index + 1}</span>
          <strong aria-current={index === current ? "step" : undefined}>
            {step}
          </strong>
        </li>
      ))}
    </ol>
  );
}

// Render an accessible error summary linked to invalid fields.
export function ErrorSummary({ errors }: { errors: Record<string, string> }) {
  const entries = Object.entries(errors);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (entries.length > 0) ref.current?.focus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entries.length]);
  if (entries.length === 0) return null;
  return (
    <div className="error-summary" ref={ref} role="alert" tabIndex={-1}>
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
