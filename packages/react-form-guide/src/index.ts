import {
  useAgent,
  useFrontendTools,
  UseAgentUpdate,
} from "@copilotkit/react-core/v2";
import { useEffect, useSyncExternalStore } from "react";

import {
  createAdaptiveFormFrontendTools,
  createFormIntelligenceState,
  createFrontendToolHandlers,
  type FormAdapter,
  type FormIntelligenceSource,
} from "./core";

export {
  createAdaptiveFormFrontendTools,
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
 * Synchronizes Form Intelligence state and registers browser-side form tools.
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

  useFrontendTools(
    createAdaptiveFormFrontendTools(adapter, agentId),
    [adapter, agentId],
  );

  return null;
}
