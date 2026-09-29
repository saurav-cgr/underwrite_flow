import {
  expect,
  test,
  type APIRequestContext,
} from "@playwright/test";

const APPLICANT = {
  email: "applicant@synthetic.test",
  password: "underwriteflow-demo-applicant",
};
const ADMINISTRATOR = {
  email: "administrator@synthetic.test",
  password: "underwriteflow-demo-administrator",
};
const UNDERWRITER = {
  email: "underwriter@synthetic.test",
  password: "underwriteflow-demo-underwriter",
};

// Build one valid synthetic PDF with optional extracted field lines.
function textPdf(lines: string[]): Buffer {
  const stream = [
    "BT /F1 12 Tf 72 720 Td 16 TL",
    ...lines.map((line, index) => {
      const escaped = line
        .replaceAll("\\", "\\\\")
        .replaceAll("(", "\\(")
        .replaceAll(")", "\\)");
      return `${index ? "T*\n" : ""}(${escaped}) Tj`;
    }),
    "ET",
  ].join("\n");
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
      + "/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    `<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`,
  ];
  let pdf = "%PDF-1.4\n";
  const offsets: number[] = [];
  for (const [index, object] of objects.entries()) {
    offsets.push(pdf.length);
    pdf += `${index + 1} 0 obj\n${object}\nendobj\n`;
  }
  const startxref = pdf.length;
  pdf += `xref\n0 ${objects.length + 1}\n`;
  pdf += "0000000000 65535 f \n";
  for (const offset of offsets) {
    pdf += `${String(offset).padStart(10, "0")} 00000 n \n`;
  }
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\n`;
  pdf += `startxref\n${startxref}\n%%EOF\n`;
  return Buffer.from(pdf, "latin1");
}

const EXPEDITED_PDF = textPdf([
  "requested_cover: 1000000",
  "date_of_birth: 1990-01-01",
  "occupation_type: office",
  "health_declaration: true",
  "cover_start_date: 2026-10-01",
  "holder_name: SYNTHETIC-HOLDER",
  "policy_expiry_date: 2026-09-15",
]);
const STANDARD_PDF = textPdf([
  "requested_cover: 15000000",
  "date_of_birth: 1990-01-01",
  "occupation_type: office",
  "health_declaration: true",
  "cover_start_date: 2026-10-01",
  "holder_name: SYNTHETIC-HOLDER",
  "policy_expiry_date: 2026-09-15",
]);
const SPECIALIST_PDF = textPdf([
  "requested_cover: 1000000",
  "date_of_birth: 1990-01-01",
  "occupation_type: hazardous",
  "health_declaration: true",
  "cover_start_date: 2026-10-01",
  "holder_name: SYNTHETIC-HOLDER",
  "policy_expiry_date: 2026-09-15",
]);
const EMPTY_PDF = textPdf([]);

// Sign in through the API proxy and return one bearer token.
async function signIn(
  request: APIRequestContext,
  account: { email: string; password: string },
): Promise<string> {
  const response = await request.post("/api/v1/auth/login", {
    data: account,
  });
  if (!response.ok()) throw new Error(await response.text());
  return (await response.json()).access_token;
}

// Create and submit one synthetic life case for the review queue.
async function createCase(
  request: APIRequestContext,
  token: string,
  index: number,
): Promise<string> {
  const standard = index === 1;
  const specialist = index === 2;
  const needsInformation = index === 3;
  const documentCodes = needsInformation
    ? ["identity_record", "income_record", "health_statement"]
    : specialist
      ? [
          "identity_record",
          "income_record",
          "health_statement",
          "previous_policy",
        ]
      : ["identity_record", "income_record", "previous_policy"];
  const payload = needsInformation
    ? {
        requested_cover: 1_000_000,
        date_of_birth: "1990-01-01",
        occupation_type: "office",
        health_declaration: false,
        cover_start_date: "2026-10-01",
      }
    : {
        requested_cover: standard ? 15_000_000 : 1_000_000,
        date_of_birth: "1990-01-01",
        occupation_type: specialist ? "hazardous" : "office",
        health_declaration: specialist ? false : true,
        cover_start_date: "2026-10-01",
      };
  const response = await request.post("/api/v1/cases", {
    headers: { Authorization: `Bearer ${token}` },
    data: {
      product_code: "life-individual-term",
      idempotency_key: `guidance-timing-${Date.now()}-${index}`,
      journey: "new_business",
      payload,
      document_codes: documentCodes,
    },
  });
  if (!response.ok()) throw new Error(await response.text());
  const caseId = (await response.json()).id as string;
  const pdf = needsInformation
    ? EMPTY_PDF
    : standard
      ? STANDARD_PDF
      : specialist
        ? SPECIALIST_PDF
        : EXPEDITED_PDF;
  for (const code of documentCodes) {
    const upload = await request.post(`/api/v1/cases/${caseId}/documents`, {
      headers: { Authorization: `Bearer ${token}` },
      multipart: {
        document: {
          name: `${code}.pdf`,
          mimeType: "application/pdf",
          buffer: pdf,
        },
        document_code: code,
      },
    });
    expect(upload.ok(), upload.statusText()).toBeTruthy();
  }
  const submitted = await request.post(`/api/v1/cases/${caseId}/submit`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!submitted.ok()) throw new Error(await submitted.text());
  const expectedRoutes = [
    "expedited",
    "standard",
    "specialist",
    "needs_information",
    "expedited",
  ];
  expect((await submitted.json()).recommendation.route).toBe(
    expectedRoutes[index],
  );
  return caseId;
}

// Measure each queue click until stored guidance text becomes visible.
test("guidance appears within three seconds for five synthetic cases", async ({
  page,
  request,
}) => {
  const applicant = await signIn(request, APPLICANT);
  const administrator = await signIn(request, ADMINISTRATOR);
  const product = await request.post(
    "/api/v1/products/life-individual-term/activate",
    {
      headers: { Authorization: `Bearer ${administrator}` },
      data: { version: "v3" },
    },
  );
  expect(product.ok(), product.statusText()).toBeTruthy();
  const versions = await request.get(
    "/api/v1/knowledge/versions?scope=guideline"
      + "&product_code=life-individual-term",
    { headers: { Authorization: `Bearer ${administrator}` } },
  );
  expect(versions.ok(), versions.statusText()).toBeTruthy();
  const guideline = (await versions.json()).find(
    (version: { version: string }) => version.version === "g1",
  );
  expect(guideline).toBeTruthy();
  const activation = await request.post(
    `/api/v1/knowledge/versions/${guideline.id}/activate`,
    { headers: { Authorization: `Bearer ${administrator}` } },
  );
  expect(activation.ok(), activation.statusText()).toBeTruthy();
  const caseIds = await Promise.all(
    Array.from(
      { length: 5 },
      (_, index) => createCase(request, applicant, index),
    ),
  );

  await page.goto("/");
  await page.getByLabel("Email").fill(UNDERWRITER.email);
  await page.getByLabel("Password").fill(UNDERWRITER.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(
    page.getByRole("heading", { name: "Review queue" }),
  ).toBeVisible();

  const timings: number[] = [];
  for (const caseId of caseIds) {
    const row = page.locator("tr").filter({ hasText: caseId.slice(0, 8) });
    await expect(row).toBeVisible();
    const started = Date.now();
    await row.getByRole("button", { name: "Open" }).click();
    const panel = page.locator("section.card").filter({
      has: page.getByRole("heading", { name: "Route explanation" }),
    });
    await expect(panel.getByText(/review is recommended/i)).toBeVisible({
      timeout: 3_000,
    });
    timings.push(Date.now() - started);
    await page.getByRole("button", { name: "Back to queue" }).click();
    await expect(
      page.getByRole("heading", { name: "Review queue" }),
    ).toBeVisible();
  }
  console.log(`guidance timing ms: ${timings.join(", ")}`);
  expect(Math.max(...timings)).toBeLessThan(3_000);
});
