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
