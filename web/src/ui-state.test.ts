import { describe, expect, it } from "vitest";
import {
  allDocumentCodes,
  homeScreenForRole,
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
