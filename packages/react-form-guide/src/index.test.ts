import { describe, expect, it, vi } from "vitest";

import type {
  FormContext,
  OptionQuery,
  RefreshOutcome,
  SetFormStateRequest,
} from "@adaptive-form-guide/contracts";

import {
  createAdaptiveFormFrontendTools,
  createFormIntelligenceState,
  createFrontendToolHandlers,
  type FormAdapter,
} from "./core";

const context: FormContext = {
  contractVersion: "1.0",
  formId: "test",
  configRevision: 3,
  fields: [],
  layout: [],
  actions: [],
  navigation: {},
};

function adapter(): FormAdapter {
  return {
    getContext: () => context,
    setFormState: vi.fn(
      async (request: SetFormStateRequest): Promise<RefreshOutcome> => ({
        status: "applied",
        applied: request.patches.map((patch) => patch.componentName),
        rejected: [],
        validationIssues: [],
        onChangeTriggered: false,
        previousRevision: 3,
        configRevision: 4,
        changedComponents: [],
        visibleComponents: [],
      }),
    ),
    getDropdownOptions: vi.fn(async (query: OptionQuery) => ({
      componentName: query.componentName,
      configRevision: 3,
      options: [{ id: "yes", label: "Yes", disabled: false }],
      hasMore: false,
    })),
    searchInputOptions: vi.fn(async (query: OptionQuery) => ({
      componentName: query.componentName,
      configRevision: 3,
      options: [{ id: "GB", label: "United Kingdom", disabled: false }],
      hasMore: false,
    })),
  };
}

describe("frontend tool handlers", () => {
  it("registers form operations as CopilotKit frontend tools", () => {
    const tools = createAdaptiveFormFrontendTools(
      adapter(),
      "adaptive_form_guide",
    );

    expect(tools.map((tool) => tool.name)).toEqual([
      "setFormState",
      "getDropdownOptions",
      "searchInputOptions",
    ]);
    expect(tools.every((tool) => tool.agentId === "adaptive_form_guide")).toBe(
      true,
    );
  });

  it("publishes raw form intelligence data in shared agent state", () => {
    const source = {
      formId: "test",
      jsx: '<Field componentName="companyName" />',
      idfConfig: {
        props: { companyName: { label: "Company name", sensitive: true } },
        state: { companyName: "backend-only" },
      },
    };

    expect(createFormIntelligenceState(source)).toEqual({
      formIntelligenceInput: source,
    });
  });

  it("clears shared input when no intelligence source is supplied", () => {
    expect(createFormIntelligenceState(undefined)).toEqual({
      formIntelligenceInput: null,
    });
  });

  it("validates and applies partial state", async () => {
    const instance = adapter();
    const result = await createFrontendToolHandlers(instance).setFormState({
      patches: [{ componentName: "hasSubsidiary", value: true }],
      expectedRevision: 3,
      sideEffectIntent: "allow-config-refresh",
    });
    expect(result.configRevision).toBe(4);
    expect(instance.setFormState).toHaveBeenCalledOnce();
  });

  it("does not search for underspecified terms", async () => {
    const instance = adapter();
    const result = await createFrontendToolHandlers(instance).searchInputOptions({
      componentName: "country",
      expectedRevision: 3,
      term: "u",
      page: 1,
    });
    expect(result.options).toEqual([]);
    expect(instance.searchInputOptions).not.toHaveBeenCalled();
  });
});
