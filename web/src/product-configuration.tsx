import { useEffect, useState } from "react";

import {
  ApiError,
  listProductConfigurations,
  listProductVersionHistory,
} from "./api";
import { Badge, EmptyState, PageHeading, Panel } from "./components";
import type {
  ProductConfigurationItem,
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
  }, [token]);

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
  }, [selectedCode, token]);

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
    </>
  );
}
