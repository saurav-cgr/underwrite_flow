import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";

import {
  ApiError,
  createCase,
  listCases,
  listCatalog,
  readCaseConfiguration,
  refreshSession,
  setUnauthorizedHandler,
} from "./api";
import { AdminWorkspace } from "./admin";
import { ApplicantDashboard, ProductSelection } from "./applicant";
import { ApplicationForm } from "./application-form";
import { DocumentsScreen } from "./documents";
import { RoleEntry } from "./entry";
import { JourneySelection } from "./journey-selection";
import { ProductConfiguration } from "./product-configuration";
import { TrackingScreen } from "./tracking";
import { AppShell, Button } from "./components";
import { CaseReview } from "./case-review";
import { UnderwriterQueue } from "./queue";
import { homeScreenForRole, isOpenCase } from "./ui-state";
import type {
  CaseConfiguration,
  CaseRecord,
  JourneyType,
  ProductCatalogItem,
  QueueItem,
  Screen,
  Session,
} from "./types";

// Coordinate authenticated role screens and typed API state.
export function App() {
  const [session, setSession] = useState<Session | null>(null);
  const sessionRef = useRef<Session | null>(null);
  const [screen, setScreen] = useState<Screen>("dashboard");
  const [journey, setJourney] = useState<JourneyType | null>(null);
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
  const [renewalFormDone, setRenewalFormDone] = useState(false);

  // Drop every role-scoped view and return to the entry screen.
  function resetToEntry(noticeText: string) {
    setSession(null);
    setJourney(null);
    setSelectedProduct(null);
    setCaseRecord(null);
    setConfiguration(null);
    setQueueItem(null);
    setAuditCaseId("");
    setMessage("");
    setRenewalFormDone(false);
    setScreen("dashboard");
    setNotice(noticeText);
  }

  // Keep the recovery path able to read the current in-memory credentials.
  useEffect(() => {
    sessionRef.current = session;
  }, [session]);

  // Rotate the refresh credential once, then sign out only if that fails.
  useEffect(() => {
    setUnauthorizedHandler(() => {
      const current = sessionRef.current;
      if (!current) return;
      refreshSession(current.refreshToken)
        .then((issued) => {
          setSession({
            ...current,
            token: issued.access_token,
            refreshToken: issued.refresh_token,
          });
        })
        .catch(() => {
          resetToEntry("Your session expired. Sign in again to continue.");
        });
    });
    return () => setUnauthorizedHandler(null);
  }, []);

  // Load product metadata scoped to the chosen journey, once one is chosen.
  useEffect(() => {
    if (session?.role !== "Applicant" || !journey) return;
    listCatalog(session.token, journey)
      .then(setCatalog)
      .catch(() => setMessage("Eligible products could not be loaded."));
  }, [journey, session]);

  // Restore the latest open case, and its journey, after a reload.
  useEffect(() => {
    if (session?.role !== "Applicant" || caseRecord) return;
    listCases(session.token)
      .then((cases) => {
        const latest = cases.find((item) => isOpenCase(item.status));
        if (latest) {
          setCaseRecord(latest);
          setJourney(latest.journey);
        }
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
    setJourney(null);
    setSelectedProduct(null);
    setCaseRecord(null);
    setConfiguration(null);
    setQueueItem(null);
    setAuditCaseId("");
    setRenewalFormDone(false);
    setScreen("dashboard");
  }

  // Move to a screen while preserving case and review context.
  function navigate(nextScreen: Screen) {
    setMessage("");
    setScreen(nextScreen);
  }

  // Choose a product and, for renewal, open a draft case immediately so
  // its prior-policy document can be uploaded before the renewal form.
  async function handleProductSelect(product: ProductCatalogItem) {
    setSelectedProduct(product);
    setRenewalFormDone(false);
    if (journey !== "renewal" || !session) {
      navigate("application");
      return;
    }
    try {
      const created = await createCase(session.token, {
        product_code: product.product_code,
        idempotency_key: crypto.randomUUID(),
        journey,
        payload: {},
        document_codes: [],
      });
      setCaseRecord(created);
      navigate("documents");
    } catch (error) {
      setMessage(
        error instanceof ApiError
          ? error.message
          : "The renewal case could not be started.",
      );
    }
  }

  if (!session) return <RoleEntry notice={notice} onLogin={handleLogin} />;

  let activeScreen: Screen;
  let content: ReactNode;

  if (session.role === "Applicant" && screen === "dashboard") {
    activeScreen = "dashboard";
    content = (
      <ApplicantDashboard caseRecord={caseRecord} onNavigate={navigate} />
    );
  } else if (session.role === "Applicant" && screen === "journey") {
    activeScreen = "journey";
    content = (
      <JourneySelection
        onNavigate={navigate}
        onSelect={(chosen) => {
          setJourney(chosen);
          navigate("products");
        }}
      />
    );
  } else if (
    session.role === "Applicant" &&
    screen === "products" &&
    journey
  ) {
    activeScreen = "products";
    content = (
      <ProductSelection
        catalog={catalog}
        error={message}
        onNavigate={navigate}
        onSelect={(product) => void handleProductSelect(product)}
      />
    );
  } else if (
    session.role === "Applicant" &&
    screen === "application" &&
    selectedProduct &&
    journey
  ) {
    activeScreen = "application";
    content = (
      <ApplicationForm
        caseRecord={journey === "renewal" ? caseRecord : null}
        journey={journey}
        onCreated={(created, product) => {
          setCaseRecord(created);
          setSelectedProduct(product);
          if (journey === "renewal") setRenewalFormDone(true);
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
    const priorPolicyPending = journey === "renewal" && !renewalFormDone;
    content = (
      <DocumentsScreen
        caseRecord={caseRecord}
        configuration={configuration}
        continueLabel="Continue to application"
        onCaseChange={setCaseRecord}
        onContinue={
          priorPolicyPending ? () => navigate("application") : undefined
        }
        onNavigate={navigate}
        stageFilter={priorPolicyPending ? "prior_policy" : undefined}
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
