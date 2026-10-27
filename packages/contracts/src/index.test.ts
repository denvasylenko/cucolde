import { describe, expect, it } from "vitest";

import {
  formContextSchema,
  optionQuerySchema,
  setFormStateRequestSchema,
} from "./index";

describe("contract schemas", () => {
  it("parses a versioned form context", () => {
    const context = formContextSchema.parse({
      contractVersion: "1.0",
      formId: "subsidiary",
      configRevision: 0,
      fields: [
        {
          componentName: "hasSubsidiary",
          kind: "radio",
          label: "Has subsidiary?",
        },
      ],
      layout: [],
    });

    expect(context.fields[0].visible).toBe(true);
    expect(context.fields[0].errors).toEqual([]);
  });

  it("rejects empty patches and invalid revisions", () => {
    expect(() =>
      setFormStateRequestSchema.parse({ patches: [], expectedRevision: -1 }),
    ).toThrow();
  });

  it("defaults option query pagination", () => {
    const query = optionQuerySchema.parse({
      componentName: "country",
      expectedRevision: 2,
    });
    expect(query.page).toBe(1);
  });
});
