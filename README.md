# Adaptive Form Guide

A vertical slice for guiding and filling configuration-driven React forms with
CopilotKit v2 and a Python Deep Agents supervisor.

## What is implemented

- A shared, versioned contract for form context, partial patches, option
  discovery, refresh outcomes, validation, and guidance.
- A reusable React bridge that synchronizes a serializable `{ jsx, idfConfig }`
  source through CopilotKit v2 shared agent state.
- A Python Deep Agent supervisor with Domain, Form Intelligence, and Filling
  specialists. The graph is read-only and exposes no frontend mutation tools.
- A backend-only Form Intelligence index with tree-sitter TSX parsing,
  precomputed navigation paths, flattened IDFConfig records, and RapidFuzz
  retrieval. Raw JSX and IDFConfig state is removed before any model call.
- A demo DynamicForm adapter that reproduces a Java-backed `onChange` refresh:
  the controlling `hasSubsidiary` patch reveals dependent fields, increments
  `configRevision`, and forces reassessment before the remaining patch.

## Run the demo

```bash
npm install
npm run build --workspace @adaptive-form-guide/contracts
npm run build --workspace @adaptive-form-guide/react
npm run dev
```

Open `http://localhost:5173` and select **Run guided sequence**. The deterministic
walkthrough runs without model credentials and displays the complete staged
trajectory.

To enable the live agent:

```bash
cd apps/agent
export OPENAI_API_KEY=...
uv sync
uv run adaptive-form-agent
```

Start the frontend with the live runtime URL:

```bash
VITE_AGENT_URL=http://localhost:8000/agent/adaptive-form-guide npm run dev
```

When `VITE_AGENT_URL` is absent, the demo intentionally runs in deterministic
walkthrough mode and does not mount the CopilotKit runtime connection.

Models are configurable with `FORM_GUIDE_SUPERVISOR_MODEL`,
`FORM_GUIDE_DOMAIN_MODEL`, `FORM_GUIDE_INTELLIGENCE_MODEL`, and
`FORM_GUIDE_FILLING_MODEL`.

## Verify

```bash
npm test
npm run build --workspace @adaptive-form-guide/contracts
npm run build --workspace @adaptive-form-guide/react
npm run build --workspace @adaptive-form-guide/demo
cd apps/agent && uv run pytest
```

## Safety boundary

The Python service never receives datasource URLs or Java service clients.
Dropdown and smart-search calls execute through the authenticated host frontend.
All writes carry an expected configuration revision, target visible/enabled
fields only, and return deterministic validation and visibility changes.

Submit, save-draft, navigation, table, overlay, and file-upload operations are
intentionally outside this vertical slice.

## Dependency note

`npm audit --omit=dev` currently reports advisories in CopilotKit's transitive
rendering stack (`katex` and legacy nested `zod` copies). npm's proposed
automatic fix downgrades CopilotKit across a breaking boundary, so this
prototype does not apply it. Pin and approve an organization-supported
CopilotKit release before production deployment.

See [DynamicForm integration](docs/dynamic-form-integration.md) for the mapping
from the screenshot-derived interfaces to the package adapter.
