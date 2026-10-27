import { describe, expect, it } from "vitest";

import { MockDynamicFormAdapter } from "./mockDynamicForm";

describe("MockDynamicFormAdapter", () => {
  it("publishes JSX and current IDFConfig for backend intelligence", () => {
    const adapter = new MockDynamicFormAdapter();
    const source = adapter.getIntelligenceSource();
    const props = source.idfConfig.props as Record<
      string,
      Record<string, unknown>
    >;
    const state = source.idfConfig.state as Record<string, unknown>;

    expect(source.formId).toBe("subsidiary-details");
    expect(source.jsx).toContain('componentName="subsidiaryCountry"');
    expect(props.subsidiaryCountry.visible).toBe(false);
    expect(state.companyName).toBe("Acme Holdings");
    expect(source.idfConfig.events).toEqual({
      onChange: { hasSubsidiary: true },
    });
  });

  it("refreshes configuration after the controlling patch", async () => {
    const adapter = new MockDynamicFormAdapter();
    const result = await adapter.setFormState({
      patches: [{ componentName: "hasSubsidiary", value: "yes" }],
      expectedRevision: 0,
      sideEffectIntent: "allow-config-refresh",
    });

    expect(result.onChangeTriggered).toBe(true);
    expect(result.changedComponents).toEqual([
      "subsidiaryName",
      "subsidiaryCountry",
      "parentCompany",
    ]);
    expect(adapter.getContext().configRevision).toBe(1);
    expect(
      adapter
        .getContext()
        .fields.find((field) => field.componentName === "subsidiaryName")?.visible,
    ).toBe(true);
    const source = adapter.getIntelligenceSource();
    const props = source.idfConfig.props as Record<
      string,
      Record<string, unknown>
    >;
    expect(props.subsidiaryName.visible).toBe(true);
  });

  it("rejects stale and hidden-field patches", async () => {
    const adapter = new MockDynamicFormAdapter();
    const hidden = await adapter.setFormState({
      patches: [{ componentName: "subsidiaryName", value: "Hidden Ltd" }],
      expectedRevision: 0,
      sideEffectIntent: "allow-config-refresh",
    });
    expect(hidden.status).toBe("rejected");

    const stale = await adapter.setFormState({
      patches: [{ componentName: "companyName", value: "New name" }],
      expectedRevision: 9,
      sideEffectIntent: "suppress",
    });
    expect(stale.status).toBe("stale");
  });

  it("returns bounded datasource options at the current revision", async () => {
    const adapter = new MockDynamicFormAdapter();
    const result = await adapter.searchInputOptions({
      componentName: "parentCompany",
      expectedRevision: 0,
      term: "glob",
      page: 1,
    });
    expect(result.options.map((option) => option.id)).toEqual(["globex"]);
  });
});
