import os

from ag_ui_langgraph import add_langgraph_fastapi_endpoint
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .agents import build_agui_agent
from .settings import settings


def create_app(include_agent: bool | None = None) -> FastAPI:
    if include_agent is None:
        include_agent = (
            os.getenv("FORM_GUIDE_AGENT_ENABLED", "").lower() == "true"
            or bool(os.getenv("OPENAI_API_KEY"))
        )

    app = FastAPI(
        title="Adaptive Form Guide Agent",
        version="0.1.0",
        description="Python Deep Agents backend exposed through AG-UI.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            origin.strip()
            for origin in settings.cors_origins.split(",")
            if origin.strip()
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> dict[str, str | bool]:
        return {
            "status": "ok",
            "contractVersion": "1.0",
            "agentEnabled": include_agent,
        }

    if include_agent:
        add_langgraph_fastapi_endpoint(
            app,
            build_agui_agent(),
            path="/agent/adaptive-form-guide",
        )

    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run(
        "adaptive_form_agent.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
