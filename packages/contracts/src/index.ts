import { z } from "zod";

export const CONTRACT_VERSION = "1.0" as const;

export const jsonValueSchema: z.ZodType<unknown> = z.lazy(() =>
  z.union([
    z.string(),
    z.number(),
    z.boolean(),
    z.null(),
    z.array(jsonValueSchema),
    z.record(z.string(), jsonValueSchema),
  ]),
);

export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

export const fieldKindSchema = z.enum([
  "text",
  "textarea",
  "radio",
  "checkbox",
  "date",
  "dropdown",
  "search",
  "group",
  "unknown",
]);

export const choiceSchema = z.object({
  id: z.string(),
  label: z.string(),
  description: z.string().optional(),
  disabled: z.boolean().default(false),
});

export const fieldDescriptorSchema = z.object({
  componentName: z.string().min(1),
  kind: fieldKindSchema,
  label: z.string(),
  helpText: z.string().optional(),
  value: jsonValueSchema.optional(),
  required: z.boolean().default(false),
  disabled: z.boolean().default(false),
  visible: z.boolean().default(true),
  sensitive: z.boolean().default(false),
  errors: z.array(z.string()).default([]),
  dependsOn: z.array(z.string()).default([]),
  choiceMode: z.enum(["none", "static", "dropdown", "search", "unknown"]).default("none"),
  staticOptions: z.array(choiceSchema).optional(),
});

export const layoutNodeSchema: z.ZodType<LayoutNode> = z.lazy(() =>
  z.object({
    componentName: z.string(),
    kind: z.string(),
    label: z.string().optional(),
    children: z.array(layoutNodeSchema).default([]),
  }),
);

export interface LayoutNode {
  componentName: string;
  kind: string;
  label?: string;
  children: LayoutNode[];
}

export const actionDescriptorSchema = z.object({
  componentName: z.string(),
  event: z.enum(["onChange", "onPartialSubmit", "onSaveDraft", "onSubmit"]),
  validate: z.array(z.string()).default([]),
  collect: z.array(z.string()).default([]),
  mutatesConfiguration: z.boolean().default(false),
});

export const formContextSchema = z.object({
  contractVersion: z.literal(CONTRACT_VERSION),
  formId: z.string(),
  configRevision: z.number().int().nonnegative(),
  fields: z.array(fieldDescriptorSchema),
  layout: z.array(layoutNodeSchema),
  actions: z.array(actionDescriptorSchema).default([]),
  navigation: z.record(z.string(), z.string()).default({}),
});

export const fieldPatchSchema = z.object({
  componentName: z.string().min(1),
  value: jsonValueSchema,
  reason: z.string().optional(),
});

export const setFormStateRequestSchema = z.object({
  patches: z.array(fieldPatchSchema).min(1),
  expectedRevision: z.number().int().nonnegative(),
  sideEffectIntent: z.enum(["allow-config-refresh", "suppress"]).default("allow-config-refresh"),
});

export const validationIssueSchema = z.object({
  componentName: z.string(),
  message: z.string(),
  code: z.string().optional(),
});

export const refreshOutcomeSchema = z.object({
  status: z.enum(["applied", "partially_applied", "rejected", "stale"]),
  applied: z.array(z.string()).default([]),
  rejected: z.array(z.string()).default([]),
  validationIssues: z.array(validationIssueSchema).default([]),
  onChangeTriggered: z.boolean().default(false),
  previousRevision: z.number().int().nonnegative(),
  configRevision: z.number().int().nonnegative(),
  changedComponents: z.array(z.string()).default([]),
  visibleComponents: z.array(z.string()).default([]),
});

export const optionQuerySchema = z.object({
  componentName: z.string().min(1),
  expectedRevision: z.number().int().nonnegative(),
  term: z.string().optional(),
  page: z.number().int().positive().default(1),
});

export const optionResultSchema = z.object({
  componentName: z.string(),
  configRevision: z.number().int().nonnegative(),
  options: z.array(choiceSchema),
  hasMore: z.boolean().default(false),
});

export const guidanceSchema = z.object({
  summary: z.string(),
  consequences: z.array(z.string()).default([]),
  unresolvedItems: z.array(z.string()).default([]),
  suggestedNavigation: z.string().optional(),
});

export type Choice = z.infer<typeof choiceSchema>;
export type FieldDescriptor = z.infer<typeof fieldDescriptorSchema>;
export type ActionDescriptor = z.infer<typeof actionDescriptorSchema>;
export type FormContext = z.infer<typeof formContextSchema>;
export type FieldPatch = z.infer<typeof fieldPatchSchema>;
export type SetFormStateRequest = z.infer<typeof setFormStateRequestSchema>;
export type ValidationIssue = z.infer<typeof validationIssueSchema>;
export type RefreshOutcome = z.infer<typeof refreshOutcomeSchema>;
export type OptionQuery = z.infer<typeof optionQuerySchema>;
export type OptionResult = z.infer<typeof optionResultSchema>;
export type Guidance = z.infer<typeof guidanceSchema>;
