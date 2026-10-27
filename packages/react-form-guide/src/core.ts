import {
  type FormContext,
  type OptionQuery,
  type OptionResult,
  type RefreshOutcome,
  type SetFormStateRequest,
  optionQuerySchema,
  setFormStateRequestSchema,
} from "@adaptive-form-guide/contracts";

export type FormIntelligenceJson =
  | string
  | number
  | boolean
  | null
  | FormIntelligenceJson[]
  | { [key: string]: FormIntelligenceJson };

export interface FormIntelligenceSource {
  [key: string]: FormIntelligenceJson;
  jsx: string;
  idfConfig: { [key: string]: FormIntelligenceJson };
  formId: string;
}

export function createFormIntelligenceState(
  source: FormIntelligenceSource | undefined,
) {
  return {
    formIntelligenceInput: source ?? null,
  };
}

export interface FormAdapter {
  getContext(): FormContext;
  getIntelligenceSource?(): FormIntelligenceSource;
  subscribe?(listener: () => void): () => void;
  setFormState(request: SetFormStateRequest): Promise<RefreshOutcome>;
  getDropdownOptions(query: OptionQuery): Promise<OptionResult>;
  searchInputOptions(query: OptionQuery): Promise<OptionResult>;
}

export function createFrontendToolHandlers(adapter: FormAdapter) {
  return {
    async setFormState(input: SetFormStateRequest): Promise<RefreshOutcome> {
      return adapter.setFormState(setFormStateRequestSchema.parse(input));
    },
    async getDropdownOptions(input: OptionQuery): Promise<OptionResult> {
      return adapter.getDropdownOptions(optionQuerySchema.parse(input));
    },
    async searchInputOptions(input: OptionQuery): Promise<OptionResult> {
      const query = optionQuerySchema.parse(input);
      if (!query.term || query.term.trim().length < 2) {
        return {
          componentName: query.componentName,
          configRevision: adapter.getContext().configRevision,
          options: [],
          hasMore: false,
        };
      }
      return adapter.searchInputOptions({ ...query, term: query.term.trim() });
    },
  };
}

export function createAdaptiveFormFrontendTools(
  adapter: FormAdapter,
  agentId?: string,
) {
  const handlers = createFrontendToolHandlers(adapter);
  return [
    {
      name: "setFormState",
      description:
        "Apply typed field patches in the browser using the current configuration revision.",
      parameters: setFormStateRequestSchema,
      handler: handlers.setFormState,
      agentId,
    },
    {
      name: "getDropdownOptions",
      description:
        "Get valid dropdown options for a component from the frontend data source.",
      parameters: optionQuerySchema,
      handler: handlers.getDropdownOptions,
      agentId,
    },
    {
      name: "searchInputOptions",
      description:
        "Search valid options for a search-input component using at least two characters.",
      parameters: optionQuerySchema,
      handler: handlers.searchInputOptions,
      agentId,
    },
  ];
}
