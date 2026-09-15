import { useEffect, useState } from "react";

import {
  ApiError,
  activateProductConfiguration,
  importProductConfiguration,
  listProductConfigurations,
  listProductVersionHistory,
  previewProductConfiguration,
  validateProductConfiguration,
} from "./api";
import { Badge, Button, EmptyState, PageHeading, Panel } from "./components";
import type {
  ProductConfigurationItem,
  ProductConfigurationPreview,
  ProductVersionHistoryItem,
} from "./types";

// Browse product configurations and their immutable version history.
export function ProductConfiguration({ token }: { token: string }) {
  const [products, setProducts] = useState<ProductConfigurationItem[]>([]);
  const [selectedCode, setSelectedCode] = useState<string | null>(null);
  const [history, setHistory] = useState<ProductVersionHistoryItem[]>([]);
  const [message, setMessage] = useState("");
  const [loadingProducts, setLoadingProducts] = useState(true);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [yamlText, setYamlText] = useState("");
  const [preview, setPreview] = useState<ProductConfigurationPreview | null>(
    null,
  );
  const [working, setWorking] = useState("");
  const [productRefresh, setProductRefresh] = useState(0);
  const [historyRefresh, setHistoryRefresh] = useState(0);

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
    setLoadingHistory(true);
    setHistory([]);
    listProductVersionHistory(token, selectedCode)
      .then(setHistory)
      .catch((error) => {
        setMessage(
          error instanceof ApiError
            ? error.message
          : "Product version history could not be loaded.",
        );
      })
      .finally(() => setLoadingHistory(false));
  }, [historyRefresh, selectedCode, token]);

  // Load a selected local YAML file without sending it to the server.
  async function handleFileChange(file: File | undefined) {
    if (!file) return;
    try {
      setYamlText(await file.text());
      setPreview(null);
      setMessage("YAML loaded locally. Validate it before importing.");
    } catch {
      setMessage("The YAML file could not be read.");
    }
  }

  // Validate local YAML without persisting a configuration version.
  async function handleValidate() {
    if (!yamlText.trim()) {
      setMessage("Paste or choose a YAML configuration first.");
      return;
    }
    setWorking("validate");
    setMessage("");
    try {
      const result = await validateProductConfiguration(token, yamlText);
      setMessage(
        `Configuration ${result.product_code} ${result.version} is valid.`,
      );
    } catch (error) {
      setMessage(
        error instanceof ApiError
          ? error.message
          : "The product configuration could not be validated.",
      );
    } finally {
      setWorking("");
    }
  }

  // Preview normalized configuration counts without creating a draft.
  async function handlePreview() {
    if (!yamlText.trim()) {
      setMessage("Paste or choose a YAML configuration first.");
      return;
    }
    setWorking("preview");
    setMessage("");
    try {
      setPreview(await previewProductConfiguration(token, yamlText));
    } catch (error) {
      setMessage(
        error instanceof ApiError
          ? error.message
          : "The product configuration could not be previewed.",
      );
    } finally {
      setWorking("");
    }
  }

  // Import local YAML only after an administrator explicitly requests it.
  async function handleImport() {
    if (!yamlText.trim()) {
      setMessage("Paste or choose a YAML configuration first.");
      return;
    }
    setWorking("import");
    setMessage("");
    try {
      const result = await importProductConfiguration(token, yamlText);
      setSelectedCode(result.product_code);
      setProductRefresh((current) => current + 1);
      setHistoryRefresh((current) => current + 1);
      setMessage(
        `Draft ${result.version} imported for ${result.product_code}.`,
      );
    } catch (error) {
      setMessage(
        error instanceof ApiError
          ? error.message
          : "The product configuration could not be imported.",
      );
    } finally {
      setWorking("");
    }
  }

  // Activate one draft only after an administrator confirms the action.
  async function handleActivate(version: string) {
    if (!selectedCode) return;
    if (!window.confirm(`Activate ${selectedCode} ${version}?`)) return;
    setWorking(`activate-${version}`);
    setMessage("");
    try {
      const result = await activateProductConfiguration(
        token,
        selectedCode,
        version,
      );
      setProductRefresh((current) => current + 1);
      setHistoryRefresh((current) => current + 1);
      setMessage(
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
  return (
    <>
      <PageHeading
        eyebrow="Administrator workspace"
        title="Product configuration"
        description={
          "Inspect fictional product versions before validating, importing, "
          + "or activating a configuration."
        }
      />
      {message ? (
        <p className="form-error" role="alert">
          {message}
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
            <div className="mini-list" role="list" aria-label="Products">
              {products.map((product) => (
                <button
                  aria-pressed={product.product_code === selectedCode}
                  className="product-config-row"
                  key={product.product_code}
                  onClick={() => setSelectedCode(product.product_code)}
                  type="button"
                >
                  <span>
                    <strong>{product.title}</strong>
                    <small>{product.product_code}</small>
                  </span>
                  <Badge tone={product.status}>{product.status}</Badge>
                </button>
              ))}
            </div>
          )}
        </Panel>
        <Panel title="Version history">
          {selectedProduct ? (
            <>
              <p className="muted">
                Active version: {selectedProduct.active_version ?? "None"}
              </p>
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
                          onClick={() => handleActivate(version.version)}
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
      <div className="admin-grid">
        <Panel title="Validate and import YAML">
          <label className="field" htmlFor="product-yaml">
            <span>Product configuration YAML</span>
            <small>
              Fictional configuration only. Validation and preview do not
              change the active version.
            </small>
            <textarea
              id="product-yaml"
              onChange={(event) => setYamlText(event.target.value)}
              placeholder="product_code: fictional-product\nversion: v2"
              value={yamlText}
            />
          </label>
          <label className="upload-button">
            <input
              accept=".yaml,.yml,text/yaml,application/x-yaml"
              aria-label="Choose product configuration YAML"
              onChange={(event) => handleFileChange(event.target.files?.[0])}
              type="file"
            />
            Choose YAML file
          </label>
          <div className="form-actions">
            <Button
              disabled={Boolean(working)}
              onClick={handleValidate}
              variant="secondary"
            >
              {working === "validate" ? "Validating…" : "Validate"}
            </Button>
            <Button
              disabled={Boolean(working)}
              onClick={handlePreview}
              variant="secondary"
            >
              {working === "preview" ? "Previewing…" : "Preview"}
            </Button>
            <Button disabled={Boolean(working)} onClick={handleImport}>
              {working === "import" ? "Importing…" : "Import draft"}
            </Button>
          </div>
        </Panel>
        <Panel title="Configuration preview">
          {preview ? (
            <div className="metric-strip">
              <div>
                <strong>{preview.field_count}</strong>
                <span>Fields</span>
              </div>
              <div>
                <strong>{preview.document_count}</strong>
                <span>Documents</span>
              </div>
              <div>
                <strong>{preview.routing_rule_count}</strong>
                <span>Routing rules</span>
              </div>
            </div>
          ) : (
            <EmptyState
              title="No preview yet"
              detail="Preview valid YAML to inspect its normalized impact."
            />
          )}
        </Panel>
      </div>
    </>
  );
}
