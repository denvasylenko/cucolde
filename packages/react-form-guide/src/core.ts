import {
  type FormContext,
  type OptionQuery,
  type OptionResult,
  type RefreshOutcome,
  type SetFormStateRequest,
  optionQuerySchema,
  setFormStateRequestSchema,
} from "@adaptive-form-guide/contracts";
import { z } from "zod";

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
  getIntelligenceSource(): FormIntelligenceSource;
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

export const FORM_OPERATION_TYPE = "form-operation";

/** Interrupt payload raised by the Python filling tools. */
export const formOperationSchema = z.discriminatedUnion("operation", [
  setFormStateRequestSchema.omit({ expectedRevision: true }).extend({
    type: z.literal(FORM_OPERATION_TYPE),
    operation: z.literal("setFormState"),
  }),
  optionQuerySchema.omit({ expectedRevision: true }).extend({
    type: z.literal(FORM_OPERATION_TYPE),
    operation: z.enum(["getDropdownOptions", "searchInputOptions"]),
  }),
]);

export type FormOperation = z.infer<typeof formOperationSchema>;

/** The AG-UI `on_interrupt` event delivers the payload as a JSON string. */
export function readInterruptPayload(value: unknown): unknown {
  if (typeof value !== "string") return value;
  try {
    return JSON.parse(value);
  } catch {
    return undefined;
  }
}

export function isFormOperation(value: unknown): boolean {
  const payload = readInterruptPayload(value);
  return (
    typeof payload === "object" &&
    payload !== null &&
    (payload as { type?: unknown }).type === FORM_OPERATION_TYPE
  );
}

/**
 * Executes one agent-requested operation against the adapter. The latest
 * configuration revision is injected here, never supplied by the agent.
 */
export async function runFormOperation(adapter: FormAdapter, payload: unknown) {
  try {
    const operation = formOperationSchema.parse(readInterruptPayload(payload));
    const handlers = createFrontendToolHandlers(adapter);
    const expectedRevision = adapter.getContext().configRevision;

    if (operation.operation === "setFormState") {
      const outcome = await handlers.setFormState({
        patches: operation.patches,
        sideEffectIntent: operation.sideEffectIntent,
        expectedRevision,
      });
      return { outcome, intelligenceSource: adapter.getIntelligenceSource() };
    }
    const { type: _type, operation: name, ...query } = operation;
    return await handlers[name]({ ...query, expectedRevision });
  } catch (error) {
    return { error: error instanceof Error ? error.message : String(error) };
  }
}
