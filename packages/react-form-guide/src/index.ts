import { useAgent, UseAgentUpdate } from "@copilotkit/react-core/v2";
import { useEffect, useSyncExternalStore } from "react";

import {
  createFormIntelligenceState,
  createFrontendToolHandlers,
  type FormAdapter,
  type FormIntelligenceSource,
} from "./core";

export {
  createFormIntelligenceState,
  createFrontendToolHandlers,
  type FormAdapter,
  type FormIntelligenceJson,
  type FormIntelligenceSource,
} from "./core";

export interface AdaptiveFormGuideBridgeProps {
  adapter: FormAdapter;
  agentId?: string;
  intelligenceSource?: FormIntelligenceSource;
}

/**
 * Synchronizes a backend-only Form Intelligence source through AG-UI state.
 * The component renders nothing and should be mounted below CopilotKit.
 */
export function AdaptiveFormGuideBridge({
  adapter,
  agentId,
  intelligenceSource,
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
    const source = intelligenceSource ?? adapter.getIntelligenceSource?.();
    agent.setState({
      ...agent.state,
      ...createFormIntelligenceState(source),
    });
  }, [
    adapter,
    agent,
    context.configRevision,
    intelligenceSource,
    isReady,
  ]);

  return null;
}
