import { useState } from "react";

import {
  ApiError,
  importProductConfiguration,
  previewProductConfiguration,
  validateProductConfiguration,
} from "./api";
import { Button, EmptyState, Panel } from "./components";
import { yamlHash } from "./ui-state";
import type { ProductConfigurationPreview } from "./types";

// Validate, preview, and import one administrator-authored YAML draft.
export function ProductImport({
  token,
  onImported,
  onStatus,
}: {
  token: string;
  onImported: (productCode: string) => Promise<void>;
  onStatus: (next: { message?: string; notice?: string }) => void;
}) {
  const [yamlText, setYamlText] = useState("");
  const [preview, setPreview] = useState<ProductConfigurationPreview | null>(
    null,
  );
  const [previewHash, setPreviewHash] = useState<string | null>(null);
  const [working, setWorking] = useState("");

  // Load a selected local YAML file without sending it to the server.
  async function handleFileChange(file: File | undefined) {
    if (!file) return;
    try {
      setYamlText(await file.text());
      setPreview(null);
      setPreviewHash(null);
      onStatus({
        notice: "YAML loaded locally. Validate it before importing.",
      });
    } catch {
      onStatus({ message: "The YAML file could not be read." });
    }
  }

  // Validate local YAML without persisting a configuration version.
  async function handleValidate() {
    if (!yamlText.trim()) {
      onStatus({ message: "Paste or choose a YAML configuration first." });
      return;
    }
    setWorking("validate");
    onStatus({ message: "", notice: "" });
    try {
      const result = await validateProductConfiguration(token, yamlText);
      onStatus({
        notice:
          `Configuration ${result.product_code} ${result.version} is valid.`,
      });
    } catch (error) {
      onStatus({
        message:
          error instanceof ApiError
            ? error.message
            : "The product configuration could not be validated.",
      });
    } finally {
      setWorking("");
    }
  }

  // Preview normalized configuration counts without creating a draft.
  async function handlePreview() {
    if (!yamlText.trim()) {
      onStatus({ message: "Paste or choose a YAML configuration first." });
      return;
    }
    setWorking("preview");
    onStatus({ message: "" });
    try {
      setPreview(await previewProductConfiguration(token, yamlText));
      setPreviewHash(yamlHash(yamlText));
    } catch (error) {
      onStatus({
        message:
          error instanceof ApiError
            ? error.message
            : "The product configuration could not be previewed.",
      });
    } finally {
      setWorking("");
    }
  }

  // Import local YAML only after an administrator explicitly requests it.
  async function handleImport() {
    if (!yamlText.trim()) {
      onStatus({ message: "Paste or choose a YAML configuration first." });
      return;
    }
    setWorking("import");
    onStatus({ message: "", notice: "" });
    try {
      const result = await importProductConfiguration(token, yamlText);
      await onImported(result.product_code);
      onStatus({
        notice: `Draft ${result.version} imported for ${result.product_code}.`,
      });
    } catch (error) {
      onStatus({
        message:
          error instanceof ApiError
            ? error.message
            : "The product configuration could not be imported.",
      });
    } finally {
      setWorking("");
    }
  }

  const previewIsCurrent =
    preview !== null && previewHash === yamlHash(yamlText);
  return (
    <div className="admin-grid">
      <Panel title="Validate and import YAML">
        <label className="field" htmlFor="product-yaml">
          <span>Product configuration YAML</span>
          <small>
            Fictional configuration only. Validation and preview do not change
            the active version.
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
        {preview && !previewIsCurrent ? (
          <p className="muted" role="status">
            The YAML changed after this preview. Preview again to refresh these
            counts.
          </p>
        ) : null}
        {previewIsCurrent && preview ? (
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
  );
}
