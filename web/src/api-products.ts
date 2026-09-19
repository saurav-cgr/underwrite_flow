// Administrator product configuration and reference document calls.
import type {
  JourneyType,
  ProductCatalogItem,
  ProductConfigurationChange,
  ProductConfigurationItem,
  ProductConfigurationPreview,
  ProductVersionHistoryItem,
  ReferenceDocument,
} from "./types";
import type { BuilderConfiguration } from "./product-builder-state";
import { request, requestBlob } from "./api-core";

// Load active product fields from the backend-owned catalog, optionally
// filtered to one journey's supported products and applicable fields.
export async function listCatalog(
  token: string,
  journey?: JourneyType,
): Promise<ProductCatalogItem[]> {
  const query = journey ? `?journey=${encodeURIComponent(journey)}` : "";
  return request(`/products/catalog${query}`, token);
}

// Load all product configurations visible to an administrator.
export async function listProductConfigurations(
  token: string,
): Promise<ProductConfigurationItem[]> {
  return request("/products", token);
}

// Load immutable version history for one selected product configuration.
export async function listProductVersionHistory(
  token: string,
  productCode: string,
): Promise<ProductVersionHistoryItem[]> {
  return request(`/products/${encodeURIComponent(productCode)}/history`, token);
}

// Validate product YAML without persisting a configuration version.
export async function validateProductConfiguration(
  token: string,
  yamlText: string,
): Promise<Pick<ProductConfigurationChange, "product_code" | "version">> {
  return request("/products/validate", token, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ yaml_text: yamlText }),
  });
}

// Preview normalized configuration counts without changing persisted products.
export async function previewProductConfiguration(
  token: string,
  yamlText: string,
): Promise<ProductConfigurationPreview> {
  return request("/products/preview", token, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ yaml_text: yamlText }),
  });
}

// Import validated YAML as a draft configuration version.
export async function importProductConfiguration(
  token: string,
  yamlText: string,
): Promise<ProductConfigurationChange> {
  return request("/products/import", token, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ yaml_text: yamlText }),
  });
}

// Activate one imported product version after administrator confirmation.
export async function activateProductConfiguration(
  token: string,
  productCode: string,
  version: string,
): Promise<ProductConfigurationChange> {
  return request(
    `/products/${encodeURIComponent(productCode)}/activate`,
    token,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ version }),
    },
  );
}

// Read one persisted version's normalized configuration for the builder.
export async function readProductVersionConfiguration(
  token: string,
  productCode: string,
  version: string,
): Promise<BuilderConfiguration> {
  return request(
    `/products/${encodeURIComponent(productCode)}` +
      `/versions/${encodeURIComponent(version)}`,
    token,
  );
}

// Export one persisted version as canonical YAML text.
export async function exportProductVersion(
  token: string,
  productCode: string,
  version: string,
): Promise<string> {
  const { blob } = await requestBlob(
    `/products/${encodeURIComponent(productCode)}` +
      `/versions/${encodeURIComponent(version)}/export`,
    token,
  );
  return blob.text();
}

// Attach one administrator reference document to a product version.
export async function uploadReference(
  token: string,
  productCode: string,
  version: string,
  file: File,
): Promise<ReferenceDocument> {
  const form = new FormData();
  form.append("reference", file);
  form.append("version", version);
  return request(
    `/products/${encodeURIComponent(productCode)}/references`,
    token,
    { method: "POST", body: form },
  );
}

// List reference documents for one product, optionally for one version.
export async function listReferences(
  token: string,
  productCode: string,
  version?: string,
): Promise<ReferenceDocument[]> {
  const query = version ? `?version=${encodeURIComponent(version)}` : "";
  return request(
    `/products/${encodeURIComponent(productCode)}/references${query}`,
    token,
  );
}

// Remove one reference document from a product configuration.
export async function deleteReference(
  token: string,
  productCode: string,
  referenceId: string,
): Promise<void> {
  await request(
    `/products/${encodeURIComponent(productCode)}/references/${referenceId}`,
    token,
    { method: "DELETE" },
  );
}
