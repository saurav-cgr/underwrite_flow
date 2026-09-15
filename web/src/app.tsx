import { useEffect, useState } from "react";

import { listCases, listCatalog } from "./api";
import { AdminWorkspace } from "./admin";
import {
  ApplicantDashboard,
  ApplicationForm,
  ProductSelection,
} from "./applicant";
import { DocumentsScreen } from "./documents";
import { RoleEntry } from "./entry";
import { ProductConfiguration } from "./product-configuration";
import { TrackingScreen } from "./tracking";
import { AppShell, Button } from "./components";
import { CaseReview, UnderwriterQueue } from "./staff";
import { homeScreenForRole, isOpenCase } from "./ui-state";
import type {
  CaseRecord,
  ProductCatalogItem,
  QueueItem,
  Screen,
  Session,
} from "./types";

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

  // Restore the latest open case and its product after a reload.
  useEffect(() => {
    if (session?.role !== "Applicant" || caseRecord) return;
    listCases(session.token)
      .then((cases) => {
        const latest = cases.find((item) => isOpenCase(item.status));
        if (!latest) return;
        setCaseRecord(latest);
        const match = catalog.find(
          (item) => item.product_code === latest.product_code,
        );
        if (match) setSelectedProduct(match);
      })
      .catch(() => setMessage("Existing cases could not be loaded."));
  }, [catalog, caseRecord, session]);

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

  if (session.role === "Administrator" && screen === "product_config") {
    return (
      <AppShell
        role={session.role}
        screen={screen}
        onNavigate={navigate}
        onSignOut={handleSignOut}
      >
        <ProductConfiguration token={session.token} />
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
