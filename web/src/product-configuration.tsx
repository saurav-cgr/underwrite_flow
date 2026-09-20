import { useEffect, useState } from "react";

import {
  ApiError,
  activateProductConfiguration,
  listProductConfigurations,
  listProductVersionHistory,
  readProductVersionConfiguration,
} from "./api";
import { Badge, Button, EmptyState, PageHeading, Panel } from "./components";
import { ConfirmDialog } from "./confirm";
import { ProductBuilder } from "./product-builder";
import { ProductImport } from "./product-import";
import type {
  BuilderConfiguration,
  ProductFamily,
} from "./product-builder-state";
import { ReferenceDocuments } from "./reference-documents";
import type {
  ProductConfigurationItem,
  ProductVersionHistoryItem,
} from "./types";

type BuilderRequest =
  | { source: "blank"; family: ProductFamily }
  | {
      source: "clone";
      family: ProductFamily;
      activeConfiguration: BuilderConfiguration;
    }
  | {
      source: "upload";
      family: ProductFamily;
      activeConfiguration: BuilderConfiguration;
    };

const FAMILIES: { value: ProductFamily; label: string }[] = [
  { value: "motor", label: "Motor" },
  { value: "life", label: "Life" },
  { value: "health", label: "Health" },
];

// Browse product configurations and their immutable version history.
export function ProductConfiguration({ token }: { token: string }) {
  const [products, setProducts] = useState<ProductConfigurationItem[]>([]);
  const [selectedCode, setSelectedCode] = useState<string | null>(null);
  const [history, setHistory] = useState<ProductVersionHistoryItem[]>([]);
  const [message, setMessage] = useState("");
  const [notice, setNotice] = useState("");
  const [loadingProducts, setLoadingProducts] = useState(true);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [working, setWorking] = useState("");
  const [productRefresh, setProductRefresh] = useState(0);
  const [pendingVersion, setPendingVersion] = useState<string | null>(null);
  const [choosingFamily, setChoosingFamily] = useState(false);
  const [builder, setBuilder] = useState<BuilderRequest | null>(null);

  // Load every administrator-visible product configuration on entry.
  useEffect(() => {
    setLoadingProducts(true);
    listProductConfigurations(token)
      .then((items) => {
        setProducts(items);
        setSelectedCode((current) => current ?? items[0]?.product_code ?? null);
      })
      .catch((error) => {
        setMessage(
          error instanceof ApiError
            ? error.message
          : "Product configurations could not be loaded.",
        );
      })
      .finally(() => setLoadingProducts(false));
  }, [productRefresh, token]);

  // Load immutable history whenever the selected product changes.
  useEffect(() => {
    if (!selectedCode) return;
    setHistory([]);
    void refreshHistory(selectedCode);
  }, [selectedCode, token]);

  // Reload the selected product's history and await the result.
  async function refreshHistory(code: string) {
    setLoadingHistory(true);
    try {
      setHistory(await listProductVersionHistory(token, code));
    } catch (error) {
      setMessage(
        error instanceof ApiError
          ? error.message
          : "Product version history could not be loaded.",
      );
    } finally {
      setLoadingHistory(false);
    }
  }

  // Select a freshly imported draft and reload its version history.
  async function handleImported(productCode: string) {
    setSelectedCode(productCode);
    setProductRefresh((current) => current + 1);
    await refreshHistory(productCode);
  }

  // Open the guided builder blank, pinned to the chosen family.
  function startBlankBuilder(family: ProductFamily) {
    setChoosingFamily(false);
    setBuilder({ source: "blank", family });
  }

  // Load the selected product's active configuration and open it as a
  // clone, so the new draft starts from an already-valid version.
  async function startCloneBuilder() {
    if (!selectedProduct?.active_version) return;
    setMessage("");
    try {
      const configuration = await readProductVersionConfiguration(
        token,
        selectedProduct.product_code,
        selectedProduct.active_version,
      );
      setBuilder({
        source: "clone",
        family: selectedProduct.family as ProductFamily,
        activeConfiguration: configuration,
      });
    } catch (error) {
      setMessage(
        error instanceof ApiError
          ? error.message
          : "The active configuration could not be loaded.",
      );
    }
  }

  // Open the guided builder pre-filled from an uploaded YAML's preview.
  function startUploadBuilder(configuration: BuilderConfiguration) {
    setBuilder({
      source: "upload",
      family: configuration.family,
      activeConfiguration: configuration,
    });
  }

  // Close the guided builder once its draft has imported or been cancelled.
  async function finishBuilder(productCode: string) {
    setBuilder(null);
    await handleImported(productCode);
  }

  // Report a nested panel outcome in the screen-level message area.
  function reportStatus(next: { message?: string; notice?: string }) {
    if (next.message !== undefined) setMessage(next.message);
    if (next.notice !== undefined) setNotice(next.notice);
  }

  // Ask before activating a version, which changes what new cases pin.
  function requestActivate(version: string) {
    if (!selectedCode) return;
    setPendingVersion(version);
  }

  // Activate the confirmed version and reload the version history.
  async function confirmActivate() {
    const version = pendingVersion;
    if (!selectedCode || version === null) return;
    setPendingVersion(null);
    setWorking(`activate-${version}`);
    setMessage("");
    setNotice("");
    try {
      const result = await activateProductConfiguration(
        token,
        selectedCode,
        version,
      );
      setProductRefresh((current) => current + 1);
      await refreshHistory(selectedCode);
      setNotice(
        `Version ${result.version} is active for ${result.product_code}.`,
      );
    } catch (error) {
      setMessage(
        error instanceof ApiError
          ? error.message
          : "The product configuration could not be activated.",
      );
    } finally {
      setWorking("");
    }
  }

  const selectedProduct = products.find(
    (product) => product.product_code === selectedCode,
  );
  const activeVersion = history.find(
    (item) => item.version === selectedProduct?.active_version,
  );
  const activeMetadata = activeVersion
    ? [
        activeVersion.content_hash.slice(0, 8),
        activeVersion.activated_at
          ? new Date(activeVersion.activated_at).toLocaleString()
          : null,
      ]
        .filter(Boolean)
        .join(" · ")
    : "";
  return (
    <>
      <PageHeading
        action={
          <Button
            onClick={() => setChoosingFamily((current) => !current)}
            variant="secondary"
          >
            Create product
          </Button>
        }
        eyebrow="Administrator workspace"
        title="Product configuration"
        description={
          "Inspect fictional product versions before validating, importing, "
          + "or activating a configuration."
        }
      />
      {choosingFamily ? (
        <div className="form-actions">
          {FAMILIES.map((option) => (
            <Button
              key={option.value}
              onClick={() => startBlankBuilder(option.value)}
              variant="secondary"
            >
              {option.label}
            </Button>
          ))}
        </div>
      ) : null}
      {message ? (
        <p className="form-error" role="alert">
          {message}
        </p>
      ) : null}
      {notice ? (
        <p className="form-notice" role="status">
          {notice}
        </p>
      ) : null}
      <div className="admin-grid">
        <Panel title="Configured products">
          {loadingProducts ? (
            <p className="muted" role="status">
              Loading product configurations.
            </p>
          ) : products.length === 0 ? (
            <EmptyState
              title="No products configured"
              detail="Import a fictional configuration to create one."
            />
          ) : (
            <ul aria-label="Products" className="mini-list">
              {products.map((product) => (
                <li key={product.product_code}>
                  <button
                    aria-pressed={product.product_code === selectedCode}
                    className="product-config-row"
                    onClick={() => setSelectedCode(product.product_code)}
                    type="button"
                  >
                    <span>
                      <strong>{product.title}</strong>
                      <small>{product.product_code}</small>
                    </span>
                    <Badge tone={product.status}>{product.status}</Badge>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Panel>
        <Panel title="Version history">
          {selectedProduct ? (
            <>
              <p className="muted">
                Active version: {selectedProduct.active_version ?? "None"}
                {activeMetadata ? ` · ${activeMetadata}` : ""}
              </p>
              {selectedProduct.active_version ? (
                <Button
                  onClick={() => void startCloneBuilder()}
                  variant="secondary"
                >
                  Create version
                </Button>
              ) : null}
              {loadingHistory ? (
                <p className="muted" role="status">
                  Loading version history.
                </p>
              ) : history.length === 0 ? (
                <p className="muted" role="status">
                  No versions are available for this product.
                </p>
              ) : (
                <div className="mini-list" role="list">
                  {history.map((version) => (
                    <div
                      className="mini-row"
                      key={version.version}
                      role="listitem"
                    >
                      <span>{version.version}</span>
                      <Badge tone={version.status}>{version.status}</Badge>
                      {version.status === "active" ? null : (
                        <Button
                          disabled={Boolean(working)}
                          onClick={() => requestActivate(version.version)}
                          variant="secondary"
                        >
                          {working === `activate-${version.version}`
                            ? "Activating…"
                            : "Activate"}
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : (
            <EmptyState
              title="Choose a product"
              detail="Select a configuration to inspect its version history."
            />
          )}
        </Panel>
      </div>
      {builder ? (
        <Panel title="Guided builder">
          <div className="form-actions">
            <Button onClick={() => setBuilder(null)} variant="quiet">
              Close builder
            </Button>
          </div>
          <ProductBuilder
            activeConfiguration={
              builder.source === "blank"
                ? undefined
                : builder.activeConfiguration
            }
            family={builder.family}
            onImported={(code) => void finishBuilder(code)}
            onStatus={reportStatus}
            source={builder.source}
            token={token}
          />
        </Panel>
      ) : null}
      <ProductImport
        onHydrate={startUploadBuilder}
        onImported={handleImported}
        onStatus={reportStatus}
        token={token}
      />
      <ReferenceDocuments
        productCode={selectedCode}
        token={token}
        versions={history}
      />
      {pendingVersion ? (
        <ConfirmDialog
          confirmLabel="Activate version"
          detail={
            `${selectedCode} ${pendingVersion} becomes the version new `
            + "cases pin."
          }
          onCancel={() => setPendingVersion(null)}
          onConfirm={() => void confirmActivate()}
          title="Activate this version?"
        />
      ) : null}
    </>
  );
}
