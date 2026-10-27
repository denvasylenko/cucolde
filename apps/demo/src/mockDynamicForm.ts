import type {
  Choice,
  FieldDescriptor,
  FormContext,
  OptionQuery,
  OptionResult,
  RefreshOutcome,
  SetFormStateRequest,
  ValidationIssue,
} from "@adaptive-form-guide/contracts";
import type {
  FormAdapter,
  FormIntelligenceSource,
} from "@adaptive-form-guide/react";

type FormIntelligenceJson = FormIntelligenceSource["idfConfig"][string];

const formJsx = `
<DynamicForm componentName="subsidiaryForm">
  <Section componentName="companyDetails" title="Company details">
    <TextInput componentName="companyName" label="Company name" />
    <RadioGroup
      componentName="hasSubsidiary"
      label="Does the company have a subsidiary?"
    />
    <Accordion componentName="subsidiaryDetails" title="Subsidiary details">
      <TextInput componentName="subsidiaryName" label="Subsidiary legal name" />
      <Dropdown componentName="subsidiaryCountry" label="Country of registration" />
      <SearchInput componentName="parentCompany" label="Ultimate parent company" />
    </Accordion>
  </Section>
</DynamicForm>
`.trim();

const countries: Choice[] = [
  { id: "GB", label: "United Kingdom", disabled: false },
  { id: "DE", label: "Germany", disabled: false },
  { id: "PL", label: "Poland", disabled: false },
  { id: "UA", label: "Ukraine", disabled: false },
  { id: "US", label: "United States", disabled: false },
];

const companies: Choice[] = [
  { id: "globex", label: "Globex Corporation", disabled: false },
  { id: "initech", label: "Initech Holdings", disabled: false },
  { id: "umbrella", label: "Umbrella Group", disabled: false },
  { id: "wayne", label: "Wayne Enterprises", disabled: false },
];

const initialFields: FieldDescriptor[] = [
  {
    componentName: "companyName",
    kind: "text",
    label: "Company name",
    value: "Acme Holdings",
    required: true,
    disabled: false,
    visible: true,
    sensitive: false,
    errors: [],
    dependsOn: [],
    choiceMode: "none",
  },
  {
    componentName: "hasSubsidiary",
    kind: "radio",
    label: "Does the company have a subsidiary?",
    value: "no",
    required: true,
    disabled: false,
    visible: true,
    sensitive: false,
    errors: [],
    dependsOn: [],
    choiceMode: "static",
    staticOptions: [
      { id: "yes", label: "Yes", disabled: false },
      { id: "no", label: "No", disabled: false },
    ],
  },
  {
    componentName: "subsidiaryName",
    kind: "text",
    label: "Subsidiary legal name",
    required: true,
    disabled: false,
    visible: false,
    sensitive: false,
    errors: [],
    dependsOn: ["hasSubsidiary"],
    choiceMode: "none",
  },
  {
    componentName: "subsidiaryCountry",
    kind: "dropdown",
    label: "Country of registration",
    required: true,
    disabled: false,
    visible: false,
    sensitive: false,
    errors: [],
    dependsOn: ["hasSubsidiary"],
    choiceMode: "dropdown",
  },
  {
    componentName: "parentCompany",
    kind: "search",
    label: "Ultimate parent company",
    required: false,
    disabled: false,
    visible: false,
    sensitive: false,
    errors: [],
    dependsOn: ["hasSubsidiary"],
    choiceMode: "search",
  },
];

function createInitialContext(): FormContext {
  return {
    contractVersion: "1.0",
    formId: "subsidiary-details",
    configRevision: 0,
    fields: structuredClone(initialFields),
    layout: [
      {
        componentName: "companyDetails",
        kind: "section",
        label: "Company details",
        children: [
          { componentName: "companyName", kind: "text", children: [] },
          { componentName: "hasSubsidiary", kind: "radio", children: [] },
          {
            componentName: "subsidiaryDetails",
            kind: "conditional-section",
            children: [
              { componentName: "subsidiaryName", kind: "text", children: [] },
              { componentName: "subsidiaryCountry", kind: "dropdown", children: [] },
              { componentName: "parentCompany", kind: "search", children: [] },
            ],
          },
        ],
      },
    ],
    actions: [
      {
        componentName: "hasSubsidiary",
        event: "onChange",
        validate: ["hasSubsidiary"],
        collect: ["hasSubsidiary"],
        mutatesConfiguration: true,
      },
    ],
    navigation: { subsidiaryDetails: "Company / Subsidiary details" },
  };
}

export class MockDynamicFormAdapter implements FormAdapter {
  private context = createInitialContext();
  private listeners = new Set<() => void>();

  getContext = (): FormContext => this.context;

  getIntelligenceSource = (): FormIntelligenceSource => {
    const props: Record<string, FormIntelligenceJson> = {};
    const state: Record<string, FormIntelligenceJson> = {};

    for (const field of this.context.fields) {
      props[field.componentName] = {
        kind: field.kind,
        label: field.label,
        helpText: field.helpText ?? null,
        required: field.required,
        disabled: field.disabled,
        visible: field.visible,
        sensitive: field.sensitive,
        dependsOn: field.dependsOn,
        choiceMode: field.choiceMode,
      };
      if (field.value !== undefined) {
        state[field.componentName] = field.value as FormIntelligenceJson;
      }
    }

    const actions = this.context.actions.map((action) => ({
      componentName: action.componentName,
      event: action.event,
      validate: action.validate,
      collect: action.collect,
      mutatesConfiguration: action.mutatesConfiguration,
    }));
    const onChange = Object.fromEntries(
      actions
        .filter((action) => action.event === "onChange")
        .map((action) => [action.componentName, true]),
    );

    return {
      formId: this.context.formId,
      jsx: formJsx,
      idfConfig: { props, state, actions, events: { onChange } },
    };
  };

  subscribe = (listener: () => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  reset = () => {
    this.context = createInitialContext();
    this.emit();
  };

  private emit() {
    this.listeners.forEach((listener) => listener());
  }

  async setFormState(request: SetFormStateRequest): Promise<RefreshOutcome> {
    const previousRevision = this.context.configRevision;
    if (request.expectedRevision !== previousRevision) {
      return this.outcome("stale", previousRevision, [], request.patches.map((p) => p.componentName));
    }

    const fields = structuredClone(this.context.fields);
    const applied: string[] = [];
    const rejected: string[] = [];
    const validationIssues: ValidationIssue[] = [];

    for (const patch of request.patches) {
      const field = fields.find((candidate) => candidate.componentName === patch.componentName);
      if (!field || !field.visible || field.disabled) {
        rejected.push(patch.componentName);
        continue;
      }
      if (field.required && (patch.value === "" || patch.value === null)) {
        rejected.push(patch.componentName);
        validationIssues.push({
          componentName: patch.componentName,
          message: "A value is required.",
          code: "required",
        });
        continue;
      }
      field.value = patch.value;
      field.errors = [];
      applied.push(patch.componentName);
    }

    const controlsVisibility =
      request.sideEffectIntent === "allow-config-refresh" &&
      applied.includes("hasSubsidiary");
    const hasSubsidiary =
      fields.find((field) => field.componentName === "hasSubsidiary")?.value === "yes";
    const changedComponents: string[] = [];

    if (controlsVisibility) {
      await new Promise((resolve) => setTimeout(resolve, 180));
      for (const name of ["subsidiaryName", "subsidiaryCountry", "parentCompany"]) {
        const field = fields.find((candidate) => candidate.componentName === name);
        if (field && field.visible !== hasSubsidiary) {
          field.visible = hasSubsidiary;
          changedComponents.push(name);
        }
      }
    }

    this.context = {
      ...this.context,
      configRevision: previousRevision + 1,
      fields,
    };
    this.emit();

    return {
      status:
        rejected.length === 0
          ? "applied"
          : applied.length > 0
            ? "partially_applied"
            : "rejected",
      applied,
      rejected,
      validationIssues,
      onChangeTriggered: controlsVisibility,
      previousRevision,
      configRevision: this.context.configRevision,
      changedComponents,
      visibleComponents: fields
        .filter((field) => field.visible)
        .map((field) => field.componentName),
    };
  }

  async getDropdownOptions(query: OptionQuery): Promise<OptionResult> {
    return this.optionsResult(query, query.componentName === "subsidiaryCountry" ? countries : []);
  }

  async searchInputOptions(query: OptionQuery): Promise<OptionResult> {
    const term = query.term?.toLocaleLowerCase() ?? "";
    const matches =
      query.componentName === "parentCompany"
        ? companies.filter((choice) => choice.label.toLocaleLowerCase().includes(term))
        : [];
    return this.optionsResult(query, matches);
  }

  private optionsResult(query: OptionQuery, options: Choice[]): OptionResult {
    if (query.expectedRevision !== this.context.configRevision) {
      return {
        componentName: query.componentName,
        configRevision: this.context.configRevision,
        options: [],
        hasMore: false,
      };
    }
    return {
      componentName: query.componentName,
      configRevision: this.context.configRevision,
      options,
      hasMore: false,
    };
  }

  private outcome(
    status: RefreshOutcome["status"],
    revision: number,
    applied: string[],
    rejected: string[],
  ): RefreshOutcome {
    return {
      status,
      applied,
      rejected,
      validationIssues: [],
      onChangeTriggered: false,
      previousRevision: revision,
      configRevision: revision,
      changedComponents: [],
      visibleComponents: this.context.fields
        .filter((field) => field.visible)
        .map((field) => field.componentName),
    };
  }
}
