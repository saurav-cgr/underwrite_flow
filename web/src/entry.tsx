import { useState } from "react";
import type { FormEvent } from "react";

import { ApiError, createSession, readSession } from "./api";
import { BrandMark, Button } from "./components";
import { Icon } from "./icons";
import type { IconName } from "./icons";
import type { Role, Session } from "./types";

const DEMO_ACCOUNTS: {
  label: string;
  email: string;
  password: string;
  role: Role;
  icon: IconName;
}[] = [
  {
    label: "Applicant",
    email: "applicant@synthetic.test",
    password: "underwriteflow-demo-applicant",
    role: "Applicant",
    icon: "user",
  },
  {
    label: "Underwriter",
    email: "underwriter@synthetic.test",
    password: "underwriteflow-demo-underwriter",
    role: "Underwriter",
    icon: "file",
  },
  {
    label: "Administrator",
    email: "administrator@synthetic.test",
    password: "underwriteflow-demo-administrator",
    role: "Administrator",
    icon: "settings",
  },
];

// Render the role entry point with paste-friendly demo credentials.
export function RoleEntry({
  notice,
  onLogin,
}: {
  notice?: string;
  onLogin: (session: Session) => void;
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [working, setWorking] = useState(false);

  // Authenticate a role and resolve its current persisted status.
  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setWorking(true);
    setMessage("");
    try {
      const response = await createSession(email, password);
      const identity = await readSession(response.token);
      onLogin({
        token: response.token,
        role: identity.role,
        sub: identity.sub,
        email,
      });
    } catch (error) {
      setMessage(
        error instanceof ApiError
          ? error.message
          : "Sign in failed. Check the demo credentials.",
      );
    } finally {
      setWorking(false);
    }
  }

  // Fill a synthetic account without hiding its credentials from the user.
  function fillDemoAccount(account: (typeof DEMO_ACCOUNTS)[number]) {
    setEmail(account.email);
    setPassword(account.password);
    setMessage("");
  }

  return (
    <main className="welcome-shell">
      <section className="welcome-copy">
        <div className="brand entry-brand">
          <BrandMark />
          <span>
            <b>Underwrite</b>Flow
          </span>
        </div>
        <p className="eyebrow">Human-governed insurance triage</p>
        <h1>Make every review easier to trust.</h1>
        <p className="welcome-lede">
          A transparent workspace for fictional applications, evidence, and
          the underwriters who make the final call.
        </p>
        <div className="trust-line">
          <Icon name="shield" />
          <span>AI assists. An underwriter remains accountable.</span>
        </div>
      </section>
      <section className="role-panel">
        <p className="eyebrow">Role entry</p>
        <h2>Sign in to continue</h2>
        <p className="muted">
          Recommendations organize work. They never approve, decline, bind,
          price, issue, renew, or cancel coverage.
        </p>
        <form onSubmit={handleSubmit}>
          <label className="field" htmlFor="email">
            <span>Email</span>
            <input
              autoComplete="username"
              id="email"
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
          </label>
          <label className="field" htmlFor="password">
            <span>Password</span>
            <input
              autoComplete="current-password"
              id="password"
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </label>
          {notice ? (
            <p className="form-notice" role="status">
              {notice}
            </p>
          ) : null}
          {message ? (
            <p className="form-error" role="alert">
              {message}
            </p>
          ) : null}
          <Button disabled={working} type="submit">
            {working ? "Signing in…" : "Sign in"}
            {working ? null : <Icon name="arrow" />}
          </Button>
        </form>
        <div className="role-options">
          <span className="eyebrow">Quick fill</span>
          {DEMO_ACCOUNTS.map((account) => (
            <button
              className="role-option"
              key={account.role}
              onClick={() => fillDemoAccount(account)}
              type="button"
            >
              <span className="role-icon">
                <Icon name={account.icon} />
              </span>
              <span>
                <b>{account.label}</b>
                <small>{account.email}</small>
              </span>
              <Icon className="chevron" name="chevron" />
            </button>
          ))}
        </div>
      </section>
    </main>
  );
}
