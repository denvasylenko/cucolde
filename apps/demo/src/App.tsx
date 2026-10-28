import { CopilotChat, CopilotKit } from "@copilotkit/react-core/v2";
import { AdaptiveFormGuideBridge, createFrontendToolHandlers } from "@adaptive-form-guide/react";
import { HttpAgent } from "@ag-ui/client";
import { type ReactNode, useState, useSyncExternalStore } from "react";

import "./App.css";
import { MockDynamicFormAdapter } from "./mockDynamicForm";

const adapter = new MockDynamicFormAdapter();
const runtimeUrl = import.meta.env.VITE_AGENT_URL as string | undefined;
const liveAgent = runtimeUrl
  ? new HttpAgent({
      agentId: "adaptive_form_guide",
      description: "Adaptive DynamicForm guide",
      url: runtimeUrl,
    })
  : undefined;

function DemoForm({ chat }: { chat?: ReactNode }) {
  const context = useSyncExternalStore(
    adapter.subscribe,
    adapter.getContext,
    adapter.getContext,
  );
  const [running, setRunning] = useState(false);

  const updateField = async (componentName: string, value: string) => {
    await adapter.setFormState({
      patches: [{ componentName, value }],
      expectedRevision: adapter.getContext().configRevision,
      sideEffectIntent: "allow-config-refresh",
    });
  };

  const runWalkthrough = async () => {
    setRunning(true);
    adapter.reset();
    const tools = createFrontendToolHandlers(adapter);

    const controlling = await tools.setFormState({
      patches: [
        {
          componentName: "hasSubsidiary",
          value: "yes",
          reason: "Reveal subsidiary details.",
        },
      ],
      expectedRevision: adapter.getContext().configRevision,
      sideEffectIntent: "allow-config-refresh",
    });

    const countryOptions = await tools.getDropdownOptions({
      componentName: "subsidiaryCountry",
      expectedRevision: controlling.configRevision,
      page: 1,
    });

    const parentMatches = await tools.searchInputOptions({
      componentName: "parentCompany",
      expectedRevision: controlling.configRevision,
      term: "glob",
      page: 1,
    });

    await tools.setFormState({
      patches: [
        { componentName: "subsidiaryName", value: "Acme UK Ltd" },
        { componentName: "subsidiaryCountry", value: countryOptions.options[0]?.id ?? "GB" },
        { componentName: "parentCompany", value: parentMatches.options[0]?.id ?? "globex" },
      ],
      expectedRevision: controlling.configRevision,
      sideEffectIntent: "allow-config-refresh",
    });
    setRunning(false);
  };

  return (
    <main>
      <header>
        <div>
          <p className="eyebrow">Adaptive Form Guide</p>
          <h1>Subsidiary details</h1>
          <p className="lede">
            A vertical slice of staged filling, dynamic configuration refresh,
            and frontend option discovery.
          </p>
        </div>
        <span className="revision">IDFConfig r{context.configRevision}</span>
      </header>

      <div className="workspace">
        <section className="panel chat-panel" aria-label="Form guide chat">
          <div className="panel-heading">
            <h2>Form guide chat</h2>
            <span>{chat ? "Connected" : "Runtime not configured"}</span>
          </div>
          {chat ?? (
            <div className="chat-disabled">
              <div>
                <strong>Live chat is disabled</strong>
                <p>
                  Set <code>OPENAI_API_KEY</code> for the Python service and start
                  the frontend with <code>VITE_AGENT_URL</code>.
                </p>
              </div>
              <textarea
                aria-label="Chat message"
                disabled
                placeholder="Ask the guide to fill this form…"
              />
            </div>
          )}
        </section>

        <section className="panel form-panel" aria-label="Dynamic form">
          <div className="panel-heading">
            <h2>Dynamic form</h2>
            <span>{context.fields.filter((field) => field.visible).length} visible fields</span>
          </div>

          {context.fields
            .filter((field) => field.visible)
            .map((field) => (
              <label className="field" key={field.componentName}>
                <span>
                  {field.label}
                  {field.required && <b aria-label="required"> *</b>}
                </span>
                {field.componentName === "hasSubsidiary" ? (
                  <select
                    value={String(field.value ?? "")}
                    onChange={(event) => void updateField(field.componentName, event.target.value)}
                  >
                    {field.staticOptions?.map((option) => (
                      <option key={option.id} value={option.id}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                ) : field.kind === "dropdown" ? (
                  <select
                    value={String(field.value ?? "")}
                    onChange={(event) => void updateField(field.componentName, event.target.value)}
                  >
                    <option value="">Select a country</option>
                    <option value="GB">United Kingdom</option>
                    <option value="DE">Germany</option>
                    <option value="UA">Ukraine</option>
                  </select>
                ) : (
                  <input
                    value={String(field.value ?? "")}
                    placeholder={field.kind === "search" ? "Search companies" : undefined}
                    onChange={(event) => void updateField(field.componentName, event.target.value)}
                  />
                )}
                <small>{field.componentName}</small>
              </label>
            ))}

          <div className="actions">
            <button disabled={running} onClick={() => void runWalkthrough()}>
              {running ? "Running staged flow…" : "Run guided sequence"}
            </button>
            <button className="secondary" onClick={adapter.reset}>
              Reset
            </button>
          </div>
        </section>
      </div>

      <footer>
        Frontend tools stay in React; datasource access stays in the Java service boundary.
      </footer>
    </main>
  );
}

function App() {
  if (!runtimeUrl) {
    return <DemoForm />;
  }

  return (
    <CopilotKit
      agentId="adaptive_form_guide"
      agents__unsafe_dev_only={{
        adaptive_form_guide: liveAgent!,
      }}
      enableInspector
    >
      <AdaptiveFormGuideBridge adapter={adapter} agentId="adaptive_form_guide" />
      <DemoForm
        chat={
          <CopilotChat
            agentId="adaptive_form_guide"
            labels={{
              modalHeaderTitle: "Adaptive Form Guide",
              welcomeMessageText:
                "hello.",
              chatInputPlaceholder: "Ask the guide to fill this form…",
            }}
          />
        }
      />
    </CopilotKit>
  );
}

export default App;
