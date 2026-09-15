import { Button, PageHeading, Panel } from "./components";
import { Icon } from "./icons";
import type { IconName } from "./icons";
import type { CaseRecord, ProductCatalogItem, Screen } from "./types";

const FAMILY_ICONS: Record<string, IconName> = {
  health: "health",
  life: "heart",
  motor: "car",
};

// Describe the product mark for a configured product family.
function familyMark(family: string): { icon: IconName; className: string } {
  const key = family.toLowerCase();
  if (key in FAMILY_ICONS) return { icon: FAMILY_ICONS[key], className: key };
  return { icon: "file", className: "other" };
}

// Show the applicant landing view and the next safe action.
export function ApplicantDashboard({
  onNavigate,
  caseRecord,
}: {
  onNavigate: (screen: Screen) => void;
  caseRecord: CaseRecord | null;
}) {
  return (
    <>
      <PageHeading
        eyebrow="Applicant dashboard"
        title="Keep your submission moving."
        description={
          "A clear view of what UnderwriteFlow has received and what "
          + "needs your attention."
        }
        action={
          <Button
            onClick={() => onNavigate(caseRecord ? "documents" : "products")}
          >
            {caseRecord ? "Open documents" : "Start an application"}
          </Button>
        }
      />
      <div className="metric-grid">
        <div className="metric">
          <span className="metric-label">Active cases</span>
          <strong>{caseRecord ? "01" : "00"}</strong>
          <span>
            {caseRecord ? "One case in progress" : "No submissions yet"}
          </span>
        </div>
        <div className="metric">
          <span className="metric-label">Human review</span>
          <strong>
            {caseRecord?.status === "underwriter_review" ? "Ready" : "—"}
          </strong>
          <span>Every final route is confirmed by an underwriter.</span>
        </div>
        <div className="metric metric-accent">
          <span className="metric-label">Data boundary</span>
          <strong>Gemini</strong>
          <span>
            Extraction uses Gemini by default. Set the fake provider to keep
            synthetic data on this machine.
          </span>
        </div>
      </div>
      {caseRecord ? (
        <div className="attention-banner">
          <span aria-hidden="true" className="banner-icon">
            <Icon name="upload" />
          </span>
          <div>
            <strong>Add supporting documents</strong>
            <p>
              Upload the requested evidence so the review team can reconcile
              your submission.
            </p>
          </div>
          <Button variant="secondary" onClick={() => onNavigate("documents")}>
            Open documents
          </Button>
        </div>
      ) : null}
      <Panel title="How the review works">
        <div className="three-up">
          <div>
            <span className="eyebrow">01 / Submit</span>
            <p>Provide fictional application facts and supporting evidence.</p>
          </div>
          <div>
            <span className="eyebrow">02 / Organize</span>
            <p>
              Rules and extraction surface missing or conflicting information.
            </p>
          </div>
          <div>
            <span className="eyebrow">03 / Confirm</span>
            <p>An authenticated underwriter confirms the final triage route.</p>
          </div>
        </div>
      </Panel>
    </>
  );
}

// Show server-owned active product configurations for selection.
export function ProductSelection({
  catalog,
  error,
  onSelect,
  onNavigate,
}: {
  catalog: ProductCatalogItem[];
  error?: string;
  onSelect: (product: ProductCatalogItem) => void;
  onNavigate: (screen: Screen) => void;
}) {
  return (
    <>
      <PageHeading
        eyebrow="New application"
        title="Choose a product."
        description={
          "The fields and document requirements below come from the active "
          + "backend configuration."
        }
        action={
          <Button variant="quiet" onClick={() => onNavigate("dashboard")}>
            Back to overview
          </Button>
        }
      />
      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}
      {catalog.length === 0 ? (
        <Panel>
          <div className="empty-state">
            <h2>No active products</h2>
            <p>
              An administrator must activate a fictional product configuration
              before applications can be submitted.
            </p>
          </div>
        </Panel>
      ) : (
        <div className="product-grid">
          {catalog.map((product) => {
            const mark = familyMark(product.family);
            return (
              <button
                className="product-card"
                key={product.product_code}
                onClick={() => onSelect(product)}
                type="button"
              >
                <span className={`product-icon ${mark.className}`}>
                  <Icon name={mark.icon} />
                </span>
                <h2>{product.title}</h2>
                <p>{product.description}</p>
                <span className="meta-line">
                  <Icon name="file" />
                  <span>Version {product.version}</span>
                </span>
                <span className="select-line">
                  <span aria-hidden="true" className="radio-mark" />
                  Select this product
                </span>
              </button>
            );
          })}
        </div>
      )}
    </>
  );
}
