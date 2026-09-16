import { useEffect, useState } from "react";
import type { ReactNode } from "react";

import {
  listCases,
  listCatalog,
  readCaseConfiguration,
  setUnauthorizedHandler,
} from "./api";
import { AdminWorkspace } from "./admin";
import { ApplicantDashboard, ProductSelection } from "./applicant";
import { ApplicationForm } from "./application-form";
import { DocumentsScreen } from "./documents";
import { RoleEntry } from "./entry";
import { ProductConfiguration } from "./product-configuration";
import { TrackingScreen } from "./tracking";
import { AppShell, Button } from "./components";
import { CaseReview } from "./case-review";
import { UnderwriterQueue } from "./queue";
import { homeScreenForRole, isOpenCase } from "./ui-state";
import type {
  CaseConfiguration,
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
  const [configuration, setConfiguration] =
    useState<CaseConfiguration | null>(null);
  const [queueItem, setQueueItem] = useState<QueueItem | null>(null);
  const [auditCaseId, setAuditCaseId] = useState("");
  const [message, setMessage] = useState("");
  const [notice, setNotice] = useState("");

  // Return to the role entry screen when a session stops being valid.
  useEffect(() => {
    setUnauthorizedHandler(() => {
      setSession(null);
      setSelectedProduct(null);
      setCaseRecord(null);
      setConfiguration(null);
      setQueueItem(null);
      setAuditCaseId("");
      setMessage("");
      setScreen("dashboard");
      setNotice("Your session expired. Sign in again to continue.");
    });
    return () => setUnauthorizedHandler(null);
  }, []);

  // Load product metadata after an applicant is authenticated.
  useEffect(() => {
    if (session?.role !== "Applicant") return;
    listCatalog(session.token)
      .then(setCatalog)
      .catch(() => setMessage("Active products could not be loaded."));
  }, [session]);

  // Restore the latest open case after a reload.
  useEffect(() => {
    if (session?.role !== "Applicant" || caseRecord) return;
    listCases(session.token)
      .then((cases) => {
        const latest = cases.find((item) => isOpenCase(item.status));
        if (latest) setCaseRecord(latest);
      })
      .catch(() => setMessage("Existing cases could not be loaded."));
  }, [caseRecord, session]);

  // Load the configuration version the applicant's case is pinned to, so a
  // newer active version never changes an existing case's requirements.
  useEffect(() => {
    if (session?.role !== "Applicant" || !caseRecord) return;
    readCaseConfiguration(session.token, caseRecord.id)
      .then(setConfiguration)
      .catch(() =>
        setMessage("The pinned configuration could not be loaded."),
      );
  }, [caseRecord?.id, session]);

  // Enter a role workspace and choose its first screen.
  function handleLogin(nextSession: Session) {
    setSession(nextSession);
    setScreen(homeScreenForRole(nextSession.role));
    setMessage("");
    setNotice("");
  }

  // Clear local UI state without retaining a bearer token.
  function handleSignOut() {
    setSession(null);
    setSelectedProduct(null);
    setCaseRecord(null);
    setConfiguration(null);
    setQueueItem(null);
    setAuditCaseId("");
    setScreen("dashboard");
  }

  // Move to a screen while preserving case and review context.
  function navigate(nextScreen: Screen) {
    setMessage("");
    setScreen(nextScreen);
  }

  if (!session) return <RoleEntry notice={notice} onLogin={handleLogin} />;

  let activeScreen: Screen;
  let content: ReactNode;

  if (session.role === "Applicant" && screen === "dashboard") {
    activeScreen = "dashboard";
    content = (
      <ApplicantDashboard caseRecord={caseRecord} onNavigate={navigate} />
    );
  } else if (session.role === "Applicant" && screen === "products") {
    activeScreen = "products";
    content = (
      <ProductSelection
        catalog={catalog}
        error={message}
        onNavigate={navigate}
        onSelect={(product) => {
          setSelectedProduct(product);
          navigate("application");
        }}
      />
    );
  } else if (
    session.role === "Applicant" &&
    screen === "application" &&
    selectedProduct
  ) {
    activeScreen = "application";
    content = (
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
    );
  } else if (
    session.role === "Applicant" &&
    screen === "documents" &&
    configuration &&
    caseRecord
  ) {
    activeScreen = "documents";
    content = (
      <DocumentsScreen
        caseRecord={caseRecord}
        configuration={configuration}
        onCaseChange={setCaseRecord}
        onNavigate={navigate}
        token={session.token}
      />
    );
  } else if (session.role === "Applicant") {
    activeScreen = "tracking";
    content = (
      <TrackingScreen
        caseRecord={caseRecord}
        onNavigate={navigate}
        token={session.token}
      />
    );
  } else if (
    session.role === "Underwriter" &&
    screen === "review" &&
    queueItem
  ) {
    activeScreen = "review";
    content = (
      <CaseReview
        item={queueItem}
        onNavigate={navigate}
        token={session.token}
      />
    );
  } else if (session.role === "Underwriter") {
    activeScreen = "queue";
    content = (
      <UnderwriterQueue
        onNavigate={navigate}
        onSelect={(item) => {
          setQueueItem(item);
          navigate("review");
        }}
        token={session.token}
      />
    );
  } else if (session.role === "Administrator" && screen === "queue") {
    activeScreen = "queue";
    content = (
      <UnderwriterQueue
        actionLabel="View audit"
        onNavigate={navigate}
        onSelect={(item) => {
          setAuditCaseId(item.case_id);
          navigate("admin");
        }}
        token={session.token}
      />
    );
  } else if (
    session.role === "Administrator" &&
    screen === "product_config"
  ) {
    activeScreen = "product_config";
    content = <ProductConfiguration token={session.token} />;
  } else {
    activeScreen = "admin";
    content = (
      <>
        <AdminWorkspace
          initialCaseId={auditCaseId}
          onNavigate={navigate}
          token={session.token}
        />
        {message ? (
          <p className="form-error" role="alert">
            {message}
          </p>
        ) : null}
      </>
    );
  }

  return (
    <AppShell
      onNavigate={navigate}
      onSignOut={handleSignOut}
      screen={activeScreen}
      session={session}
    >
      {content}
    </AppShell>
  );
}

export default App;
