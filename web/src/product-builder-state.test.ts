import { describe, expect, it } from "vitest";

import {
  blankConfiguration,
  builderCompletion,
  cloneForNewVersion,
  semanticDiff,
} from "./product-builder-state";
import type { BuilderConfiguration } from "./product-builder-state";

// Build one complete, valid fictional configuration for state tests.
function completeConfiguration(): BuilderConfiguration {
  return {
    ...blankConfiguration("motor"),
    product_code: "motor-builder-demo",
    title: "Synthetic Builder Product",
    scope: "Fictional demonstration only",
    description: "Synthetic builder configuration",
    version: "v1",
    fields: [
      {
        key: "vehicle_age",
        label: "Vehicle age",
        type: "integer",
        required: true,
        help_text: "Enter a fictional vehicle age.",
        validation: {},
        options: [],
        applies_to: ["new_business", "renewal"],
      },
    ],
    documents: [
      {
        code: "identity_record",
        title: "Synthetic identity record",
        requirement: "required",
        accepted_types: ["application/pdf"],
        stage: "supporting",
        applies_to: ["new_business", "renewal"],
      },
    ],
    routing_rules: [
      {
        code: "standard_review",
        condition: { field: "vehicle_age", operator: "greater_than", value: 0 },
        route: "standard",
        applies_to: ["new_business", "renewal"],
      },
    ],
    specialist_labels: ["motor inspection"],
  };
}

describe("blank configuration", () => {
  it("starts empty, draft, and pinned to the chosen family", () => {
    const blank = blankConfiguration("motor");
    expect(blank.family).toBe("motor");
    expect(blank.status).toBe("draft");
    expect(blank.fields).toHaveLength(0);
    expect(blank.documents).toHaveLength(0);
    expect(blank.routing_rules).toHaveLength(0);
    expect(blank.specialist_labels).toHaveLength(0);
    expect(blank.supported_journeys).toEqual(["new_business", "renewal"]);
  });
});

describe("clone for a new version", () => {
  it("locks product identity while resetting version and status", () => {
    const source = completeConfiguration();
    const cloned = cloneForNewVersion(source, "v2");
    expect(cloned.product_code).toBe(source.product_code);
    expect(cloned.family).toBe(source.family);
    expect(cloned.version).toBe("v2");
    expect(cloned.status).toBe("draft");
  });

  it("deep copies sections so editing the clone leaves source alone", () => {
    const source = completeConfiguration();
    const cloned = cloneForNewVersion(source, "v2");
    cloned.fields.push({
      key: "extra_field",
      label: "Extra field",
      type: "text",
      required: false,
      help_text: "Synthetic extra field.",
      validation: {},
      options: [],
      applies_to: ["new_business", "renewal"],
    });
    expect(source.fields).toHaveLength(1);
    expect(cloned.fields).toHaveLength(2);
  });
});

describe("local completeness checks", () => {
  it("reports every missing required section on a blank configuration", () => {
    const result = builderCompletion(blankConfiguration("motor"));
    expect(result.complete).toBe(false);
    expect(result.missingSections).toEqual(
      expect.arrayContaining([
        "fields",
        "documents",
        "routing_rules",
        "specialist_labels",
      ]),
    );
  });

  it("reports complete once every required section is populated", () => {
    const result = builderCompletion(completeConfiguration());
    expect(result.complete).toBe(true);
    expect(result.missingSections).toHaveLength(0);
  });
});

describe("stable semantic diff", () => {
  it("reports no difference when only section ordering changes", () => {
    const base = completeConfiguration();
    const reordered: BuilderConfiguration = {
      ...base,
      specialist_labels: [...base.specialist_labels],
      fields: [...base.fields].reverse(),
    };
    expect(semanticDiff(base, reordered)).toHaveLength(0);
  });

  it("reports an added field and a changed rule route", () => {
    const before = completeConfiguration();
    const after: BuilderConfiguration = {
      ...before,
      fields: [
        ...before.fields,
        {
          key: "vehicle_use",
          label: "Vehicle use",
          type: "text",
          required: false,
          help_text: "Synthetic vehicle use.",
          validation: {},
          options: [],
          applies_to: ["new_business", "renewal"],
        },
      ],
      routing_rules: [{ ...before.routing_rules[0], route: "expedited" }],
    };
    const diff = semanticDiff(before, after);
    expect(diff).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          section: "fields",
          kind: "added",
          key: "vehicle_use",
        }),
        expect.objectContaining({
          section: "routing_rules",
          kind: "changed",
          key: "standard_review",
        }),
      ]),
    );
  });

  it("reports a changed scalar identity property", () => {
    const before = completeConfiguration();
    const after: BuilderConfiguration = { ...before, title: "Renamed" };

    expect(semanticDiff(before, after)).toContainEqual({
      section: "identity",
      kind: "changed",
      key: "title",
    });
  });

  it("reports no journey difference when the order changes", () => {
    const before: BuilderConfiguration = {
      ...completeConfiguration(),
      supported_journeys: ["new_business", "renewal"],
    };
    const after: BuilderConfiguration = {
      ...before,
      supported_journeys: ["renewal", "new_business"],
    };

    expect(semanticDiff(before, after)).toHaveLength(0);
  });

  it("reports an added supported journey", () => {
    const before: BuilderConfiguration = {
      ...completeConfiguration(),
      supported_journeys: ["new_business"],
    };
    const after: BuilderConfiguration = {
      ...before,
      supported_journeys: ["new_business", "renewal"],
    };

    expect(semanticDiff(before, after)).toContainEqual({
      section: "supported_journeys",
      kind: "added",
      key: "renewal",
    });
  });
});
