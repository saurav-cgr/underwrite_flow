import { describe, expect, it } from "vitest";
import {
  allDocumentCodes,
  applicantNextStep,
  auditFacts,
  homeScreenForRole,
  identityInitials,
  isOpenCase,
  requiredDocuments,
  validateFields,
  visibleFields,
  yamlHash,
} from "./ui-state";
import type { ProductDocument, ProductField } from "./types";

const fields: ProductField[] = [
  {
    key: "member_count",
    label: "Members",
    type: "integer",
    required: true,
    help_text: "Synthetic count",
    validation: {},
    options: [],
  },
  {
    key: "continuity_months",
    label: "Continuity",
    type: "integer",
    required: true,
    help_text: "Synthetic months",
    validation: {},
    options: [],
    visible_when: { field: "member_count", equals: 2 },
  },
];

// Verify role entry points stay aligned with workspace navigation.
describe("role workspace routing", () => {
  it("opens each role in its governed first screen", () => {
    expect(homeScreenForRole("Applicant")).toBe("dashboard");
    expect(homeScreenForRole("Underwriter")).toBe("queue");
    expect(homeScreenForRole("Administrator")).toBe("admin");
  });

  it("treats only completed cases as closed", () => {
    expect(isOpenCase("completed")).toBe(false);
    expect(isOpenCase("needs_information")).toBe(true);
    expect(isOpenCase("underwriter_review")).toBe(true);
  });

  it("derives avatar initials from the demo email", () => {
    expect(identityInitials("applicant@synthetic.test")).toBe("AP");
    expect(identityInitials("underwriter@synthetic.test")).toBe("UN");
    expect(identityInitials("administrator@synthetic.test")).toBe("AD");
    expect(identityInitials("@")).toBe("??");
  });

  it("hashes identical YAML identically and changed YAML differently", () => {
    expect(yamlHash("version: v1")).toBe(yamlHash("version: v1"));
    expect(yamlHash("version: v1")).not.toBe(yamlHash("version: v2"));
    expect(yamlHash("")).toHaveLength(8);
  });
});

// Verify product-aware visibility and required-field messages.
describe("application form state", () => {
  it("validates only visible required fields", () => {
    expect(visibleFields(fields, { member_count: 1 })).toHaveLength(1);
    expect(validateFields(fields, { member_count: 1 })).toEqual({});
    expect(validateFields(fields, { member_count: 2 })).toEqual({
      continuity_months: "This field is required.",
    });
  });
});

// Verify intake sends only known document codes from the server catalog.
describe("document intake", () => {
  it("excludes not-applicable documents", () => {
    const documents: ProductDocument[] = [
      {
        code: "identity_record",
        title: "Identity",
        requirement: "required",
        accepted_types: ["application/pdf"],
      },
      {
        code: "old_record",
        title: "Old record",
        requirement: "not_applicable",
        accepted_types: ["application/pdf"],
      },
    ];
    expect(allDocumentCodes(documents)).toEqual(["identity_record"]);
    const requiredCodes = requiredDocuments(documents).map(
      (document) => document.code,
    );
    expect(requiredCodes).toEqual(["identity_record"]);
  });
});

// Verify an unprocessed case is described as unfinished, not as progressing.
describe("applicant next step", () => {
  it("tells the applicant an unprocessed case still needs documents", () => {
    const step = applicantNextStep("new");

    expect(step.screen).toBe("documents");
    expect(step.title).toContain("not finished processing");
  });

  it("points a needs-information case at the documents screen", () => {
    expect(applicantNextStep("needs_information").screen).toBe("documents");
  });

  it("asks nothing of the applicant while an underwriter reviews", () => {
    const step = applicantNextStep("underwriter_review");

    expect(step.screen).toBe("tracking");
    expect(step.detail).toContain("No action is needed");
  });

  it("describes a completed case as handed off", () => {
    expect(applicantNextStep("completed").detail).toContain("handed");
  });
});

// Verify audit details render as bounded facts instead of one raw blob.
describe("audit facts", () => {
  it("summarizes scalar, list, and nested values", () => {
    const facts = auditFacts({
      recommendation: "specialist",
      review_cycle: 0,
      conflicts: ["vehicle_age"],
      missing_information: [],
      documents: [{ id: 1 }, { id: 2 }],
      nested: { a: 1 },
    });

    expect(facts).toEqual([
      { label: "Recommendation", value: "specialist" },
      { label: "Review cycle", value: "0" },
      { label: "Conflicts", value: "vehicle_age" },
      { label: "Missing information", value: "none" },
      { label: "Documents", value: "2 records" },
      { label: "Nested", value: "structured detail" },
    ]);
  });

  it("shortens a long hash so it stays recognisable", () => {
    const hash =
      "765d638ae276115aaa407954995a899e89b246e23ec18d1511d6f04a507172dd";
    const facts = auditFacts({ product_content_hash: hash });

    expect(facts).toEqual([
      { label: "Product content hash", value: "765d638a…" },
    ]);
  });

  it("drops null values instead of rendering empty rows", () => {
    expect(auditFacts({ absent: null })).toEqual([]);
  });
});
