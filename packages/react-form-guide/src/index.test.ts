import { describe, expect, it, vi } from "vitest";

import type {
  FormContext,
  OptionQuery,
  RefreshOutcome,
  SetFormStateRequest,
} from "@adaptive-form-guide/contracts";

import {
  createFormIntelligenceState,
  createFrontendToolHandlers,
  isFormOperation,
  runFormOperation,
  type FormAdapter,
  type FormIntelligenceSource,
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

const freshSource: FormIntelligenceSource = {
  formId: "test",
  jsx: '<Field componentName="companyName" />',
  idfConfig: { props: {}, state: {}, actions: [], events: { onChange: {} } },
};

function adapter(): FormAdapter {
  return {
    getContext: () => context,
    getIntelligenceSource: () => freshSource,
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

describe("form operations requested through interrupts", () => {
  it("recognizes only form-operation payloads", () => {
    expect(isFormOperation({ type: "form-operation", operation: "x" })).toBe(
      true,
    );
    expect(
      isFormOperation(JSON.stringify({ type: "form-operation" })),
    ).toBe(true);
    expect(isFormOperation("not json")).toBe(false);
    expect(isFormOperation({ type: "approval" })).toBe(false);
    expect(isFormOperation(null)).toBe(false);
  });

  it("injects the latest revision and returns the refreshed source", async () => {
    const instance = adapter();

    const result = await runFormOperation(instance, {
      type: "form-operation",
      operation: "setFormState",
      patches: [{ componentName: "hasSubsidiary", value: "yes" }],
      sideEffectIntent: "allow-config-refresh",
    });

    expect(instance.setFormState).toHaveBeenCalledWith(
      expect.objectContaining({ expectedRevision: 3 }),
    );
    expect(result).toEqual({
      outcome: expect.objectContaining({ status: "applied", configRevision: 4 }),
      intelligenceSource: freshSource,
    });
  });

  it("accepts the JSON-string payload delivered by AG-UI", async () => {
    const instance = adapter();

    await runFormOperation(
      instance,
      JSON.stringify({
        type: "form-operation",
        operation: "setFormState",
        patches: [{ componentName: "hasSubsidiary", value: "yes" }],
        sideEffectIntent: "allow-config-refresh",
      }),
    );

    expect(instance.setFormState).toHaveBeenCalledOnce();
  });

  it("runs option lookups with the latest revision", async () => {
    const instance = adapter();

    const dropdown = await runFormOperation(instance, {
      type: "form-operation",
      operation: "getDropdownOptions",
      componentName: "country",
      page: 1,
    });
    await runFormOperation(instance, {
      type: "form-operation",
      operation: "searchInputOptions",
      componentName: "parent",
      term: "glob",
      page: 1,
    });

    expect(dropdown).toMatchObject({ options: [{ id: "yes" }] });
    expect(instance.getDropdownOptions).toHaveBeenCalledWith(
      expect.objectContaining({ expectedRevision: 3 }),
    );
    expect(instance.searchInputOptions).toHaveBeenCalledWith(
      expect.objectContaining({ expectedRevision: 3, term: "glob" }),
    );
  });

  it("returns an error instead of throwing for an invalid payload", async () => {
    const instance = adapter();

    const result = await runFormOperation(instance, {
      type: "form-operation",
      operation: "setFormState",
      patches: [],
    });

    expect(result).toHaveProperty("error");
    expect(instance.setFormState).not.toHaveBeenCalled();
  });
});

describe("frontend handlers", () => {
  it("publishes raw form intelligence data in shared agent state", () => {
    expect(createFormIntelligenceState(freshSource)).toEqual({
      formIntelligenceInput: freshSource,
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
