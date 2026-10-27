# DynamicForm integration

The source DynamicForm is not part of this repository. This adapter mapping is
based on the supplied `DynamicForm.interface.ts` screenshots.

## Host mapping

- `IDFConfig.props` becomes the normalized field list. Preserve
  `componentName`, component kind, labels, visibility, disabled/required state,
  dependencies, and choice mode.
- `IDFConfig.state` supplies current field values. Sensitive values must be
  marked and are removed before CopilotKit context publication.
- `IDFConfig.actions` and `events.onChange` become action descriptors. They tell
  Form Intelligence which fields are controlling, but do not expose datasource
  endpoints to the model.
- Static JSX source and a JSON-serializable IDFConfig projection are synchronized
  through CopilotKit shared agent state. Python indexes and clears the transient
  state before model execution. React elements, render functions, service
  instances, and callbacks are never serialized.
- The host's React Hook Form/state update path implements `setFormState`.
  Programmatic values must use the same setter and validation path as user edits.
- Existing dropdown and input-search callbacks implement
  `getDropdownOptions` and `searchInputOptions`; results are normalized to
  `{ id, label, description?, disabled }`.

## Refresh protocol

1. Compare `expectedRevision` with the current adapter revision.
2. Validate that every target field exists, is visible, enabled, and accepts the
   proposed value shape.
3. Apply a minimal controlling-field patch.
4. Allow only its configured `onChange` behavior to call the Java service.
5. Install the returned `IDFConfig`, increment `configRevision`, and report
   changed and visible component names.
6. Re-run Form Intelligence before applying dependent fields.

This avoids writing dependent values against stale props or option lists.

## Unknowns to resolve in the real host

- Whether `updateConfig` deep-merges or replaces configuration.
- Whether React Hook Form or `IDFConfig.state` is the authoritative state and
  how the two are synchronized.
- Whether programmatic `setValue` invokes configured `onChange` automatically.
- Exact option/value shapes for dropdown, combo box, and input-search controls.
- Whether a Java refresh can replace component identities or only props/state.
- Authentication, rate limits, cancellation, and pagination behavior of search
  datasources.

The production adapter must answer these points; the demo intentionally models
one explicit and testable interpretation.
