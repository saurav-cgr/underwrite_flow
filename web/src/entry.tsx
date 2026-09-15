import { useState } from "react";
import type { FormEvent } from "react";

import { ApiError, createSession, readSession } from "./api";
import { BrandMark, Button } from "./components";
import type { Role, Session } from "./types";

const DEMO_ACCOUNTS: {
  label: string;
  email: string;
  password: string;
  role: Role;
}[] = [
  {
    label: "Applicant",
    email: "applicant@synthetic.test",
    password: "underwriteflow-demo-applicant",
    role: "Applicant",
  },
  {
    label: "Underwriter",
    email: "underwriter@synthetic.test",
    password: "underwriteflow-demo-underwriter",
    role: "Underwriter",
  },
  {
    label: "Administrator",
    email: "administrator@synthetic.test",
    password: "underwriteflow-demo-administrator",
    role: "Administrator",
  },
];

// Render the role entry point with paste-friendly demo credentials.
export function RoleEntry({
  onLogin,
}: {
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
  function useDemo(account: (typeof DEMO_ACCOUNTS)[number]) {
    setEmail(account.email);
    setPassword(account.password);
    setMessage("");
  }

  return (
    <main className="entry-page">
      <section className="entry-story">
        <div className="brand entry-brand">
          <BrandMark />
          <span>
            <b>Underwrite</b>Flow
          </span>
        </div>
        <p className="eyebrow">Human-governed insurance triage</p>
        <h1>Make every review easier to trust.</h1>
        <p className="entry-copy">
          A transparent workspace for fictional applications, evidence, and
          the underwriters who make the final call.
        </p>
        <div className="entry-note">
          <span className="notice-mark" aria-hidden="true">
            i
          </span>
          <span>
            Recommendations organize work. They never approve, decline, bind,
            price, issue, renew, or cancel coverage.
          </span>
        </div>
      </section>
      <section className="entry-card">
        <p className="eyebrow">Role entry</p>
        <h2>Sign in to continue</h2>
        <p className="muted">Use a synthetic demonstration account.</p>
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
          {message ? (
            <p className="form-error" role="alert">
              {message}
            </p>
          ) : null}
          <Button disabled={working} type="submit">
            {working ? "Signing in…" : "Sign in"}
          </Button>
        </form>
        <div className="demo-list">
          <span className="eyebrow">Quick fill</span>
          {DEMO_ACCOUNTS.map((account) => (
            <button
              key={account.role}
              onClick={() => useDemo(account)}
              type="button"
            >
              <span>{account.label}</span>
              <small>{account.email}</small>
            </button>
          ))}
        </div>
      </section>
    </main>
  );
}
