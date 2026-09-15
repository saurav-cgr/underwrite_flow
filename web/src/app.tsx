import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { ApiError, createSession, listCatalog, readSession } from "./api";
import { AdminWorkspace } from "./admin";
import {
  ApplicantDashboard,
  ApplicationForm,
  ProductSelection,
} from "./applicant";
import { DocumentsScreen } from "./documents";
import { TrackingScreen } from "./tracking";
import { AppShell, Button } from "./components";
import { CaseReview, UnderwriterQueue } from "./staff";
import { homeScreenForRole } from "./ui-state";
import type {
  CaseRecord,
  ProductCatalogItem,
  QueueItem,
  Role,
  Screen,
  Session,
} from "./types";

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
function RoleEntry({ onLogin }: { onLogin: (session: Session) => void }) {
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
          <span className="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 32 32">
              <path
                d={
                  "M16 3 27 8v8c0 6.7-4.2 10.8-11 13C9.2 26.8 "
                  + "5 22.7 5 16V8l11-5Z"
                }
              />
              <path d="m10 16 4 4 8-9" />
            </svg>
          </span>
          <span>
            Underwrite<span className="brand-accent">Flow</span>
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

// Coordinate authenticated role screens and typed API state.
export function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [screen, setScreen] = useState<Screen>("dashboard");
  const [catalog, setCatalog] = useState<ProductCatalogItem[]>([]);
  const [selectedProduct, setSelectedProduct] =
    useState<ProductCatalogItem | null>(null);
  const [caseRecord, setCaseRecord] = useState<CaseRecord | null>(null);
  const [queueItem, setQueueItem] = useState<QueueItem | null>(null);
  const [message, setMessage] = useState("");

  // Load product metadata after an applicant is authenticated.
  useEffect(() => {
    if (session?.role !== "Applicant") return;
    listCatalog(session.token)
      .then(setCatalog)
      .catch(() => setMessage("Active products could not be loaded."));
  }, [session]);

  // Enter a role workspace and choose its first screen.
  function handleLogin(nextSession: Session) {
    setSession(nextSession);
    setScreen(homeScreenForRole(nextSession.role));
    setMessage("");
  }

  // Clear local UI state without retaining a bearer token.
  function handleSignOut() {
    setSession(null);
    setSelectedProduct(null);
    setCaseRecord(null);
    setQueueItem(null);
    setScreen("dashboard");
  }

  // Move to a screen while preserving case and review context.
  function navigate(nextScreen: Screen) {
    setMessage("");
    setScreen(nextScreen);
  }

  if (!session) return <RoleEntry onLogin={handleLogin} />;

  if (session.role === "Applicant" && screen === "dashboard") {
    return (
      <AppShell
        role={session.role}
        screen={screen}
        onNavigate={navigate}
        onSignOut={handleSignOut}
      >
        <ApplicantDashboard
          caseRecord={caseRecord}
          onNavigate={navigate}
        />
      </AppShell>
    );
  }

  if (session.role === "Applicant" && screen === "products") {
    return (
      <AppShell
        role={session.role}
        screen={screen}
        onNavigate={navigate}
        onSignOut={handleSignOut}
      >
        <ProductSelection
          catalog={catalog}
          error={message}
          onNavigate={navigate}
          onSelect={(product) => {
            setSelectedProduct(product);
            navigate("application");
          }}
        />
      </AppShell>
    );
  }

  if (
    session.role === "Applicant" &&
    screen === "application" &&
    selectedProduct
  ) {
    return (
      <AppShell
        role={session.role}
        screen={screen}
        onNavigate={navigate}
        onSignOut={handleSignOut}
      >
        <ApplicationForm
          onCreated={(created, product) => {
            setCaseRecord(created);
            setSelectedProduct(product);
            navigate("documents");
          }}
          onNavigate={navigate}
          product={selectedProduct}
          token={session.token}
        />
      </AppShell>
    );
  }

  if (
    session.role === "Applicant" &&
    screen === "documents" &&
    selectedProduct &&
    caseRecord
  ) {
    return (
      <AppShell
        role={session.role}
        screen={screen}
        onNavigate={navigate}
        onSignOut={handleSignOut}
      >
        <DocumentsScreen
          caseRecord={caseRecord}
          onNavigate={navigate}
          product={selectedProduct}
          token={session.token}
        />
      </AppShell>
    );
  }

  if (session.role === "Applicant") {
    return (
      <AppShell
        role={session.role}
        screen="tracking"
        onNavigate={navigate}
        onSignOut={handleSignOut}
      >
        <TrackingScreen
          caseRecord={caseRecord}
          onNavigate={navigate}
          token={session.token}
        />
      </AppShell>
    );
  }

  if (session.role === "Underwriter" && screen === "review" && queueItem) {
    return (
      <AppShell
        role={session.role}
        screen={screen}
        onNavigate={navigate}
        onSignOut={handleSignOut}
      >
        <CaseReview
          item={queueItem}
          onNavigate={navigate}
          token={session.token}
        />
      </AppShell>
    );
  }

  if (session.role === "Underwriter") {
    return (
      <AppShell
        role={session.role}
        screen="queue"
        onNavigate={navigate}
        onSignOut={handleSignOut}
      >
        <UnderwriterQueue
          onNavigate={navigate}
          onSelect={(item) => {
            setQueueItem(item);
            navigate("review");
          }}
          token={session.token}
        />
      </AppShell>
    );
  }

  if (session.role === "Administrator" && screen === "queue") {
    return (
      <AppShell
        role={session.role}
        screen={screen}
        onNavigate={navigate}
        onSignOut={handleSignOut}
      >
        <UnderwriterQueue
          onNavigate={navigate}
          onSelect={() =>
            setMessage(
              "Administrator queue inspection is read-only; open audit "
                + "history for case reconstruction.",
            )
          }
          token={session.token}
        />
      </AppShell>
    );
  }

  return (
    <AppShell
      role={session.role}
      screen="admin"
      onNavigate={navigate}
      onSignOut={handleSignOut}
    >
      <AdminWorkspace onNavigate={navigate} token={session.token} />
      {message ? (
        <p className="form-error" role="alert">
          {message}
        </p>
      ) : null}
    </AppShell>
  );
}

export default App;
