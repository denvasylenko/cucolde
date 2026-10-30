import { useAgent, useInterrupt, UseAgentUpdate } from "@copilotkit/react-core/v2";
import { createElement, useEffect, useRef, useSyncExternalStore } from "react";

import {
  createFormIntelligenceState,
  isFormOperation,
  readInterruptPayload,
  runFormOperation,
  type FormAdapter,
} from "./core";

export {
  createFormIntelligenceState,
  createFrontendToolHandlers,
  FORM_OPERATION_TYPE,
  formOperationSchema,
  isFormOperation,
  readInterruptPayload,
  runFormOperation,
  type FormAdapter,
  type FormIntelligenceJson,
  type FormIntelligenceSource,
  type FormOperation,
} from "./core";

export interface AdaptiveFormGuideBridgeProps {
  adapter: FormAdapter;
  agentId?: string;
}

function FormOperationCard({
  operation,
  result,
  resolve,
}: {
  operation: string;
  result: unknown;
  resolve: (payload?: unknown) => unknown;
}) {
  const resolved = useRef(false);
  useEffect(() => {
    if (result === null || resolved.current) return;
    resolved.current = true;
    void resolve(result);
  }, [result, resolve]);

  return createElement(
    "small",
    { className: "form-operation" },
    result === null ? `Running ${operation}…` : `Completed ${operation}`,
  );
}

/**
 * Synchronizes the Form Intelligence source into shared agent state and runs
 * form operations the agent requests through CopilotKit interrupts.
 * The component renders nothing and should be mounted below CopilotKit.
 */
export function AdaptiveFormGuideBridge({
  adapter,
  agentId,
}: AdaptiveFormGuideBridgeProps) {
  const subscribe = adapter.subscribe ?? (() => () => undefined);
  const context = useSyncExternalStore(
    subscribe,
    adapter.getContext,
    adapter.getContext,
  );
  const { agent, isReady } = useAgent({
    agentId,
    updates: [UseAgentUpdate.OnStateChanged],
  });

  useEffect(() => {
    if (!isReady) return;
    agent.setState({
      ...agent.state,
      ...createFormIntelligenceState(adapter.getIntelligenceSource()),
    });
  }, [adapter, agent, context.configRevision, isReady]);

  useInterrupt({
    agentId,
    enabled: (event) => isFormOperation(event.value),
    handler: ({ event }) => runFormOperation(adapter, event.value),
    render: ({ event, result, resolve }) =>
      createElement(FormOperationCard, {
        operation: (
          readInterruptPayload(event.value) as { operation: string }
        ).operation,
        result,
        resolve,
      }),
  });

  return null;
}
