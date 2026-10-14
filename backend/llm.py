"""Portkey model wiring. Every agent must use gpt-6-luna only."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

# Hard requirement for this homework — do not swap models.
MODEL_NAME = "gpt-6-luna"

# Keep multi-agent loops from burning tokens.
REQUEST_LIMIT = 8
TOOL_CALLS_LIMIT = 12
TEAM_LIMITS = UsageLimits(request_limit=REQUEST_LIMIT, tool_calls_limit=TOOL_CALLS_LIMIT)
MAX_DELEGATION_DEPTH = 3


class MissingModelKey(RuntimeError):
    """PORTKEY_API_KEY is not in the class root .env."""


def load_root_env() -> Path:
    root = Path(__file__).resolve()
    while root.parent != root and not (root / ".env").is_file():
        root = root.parent
    env_path = root / ".env"
    load_dotenv(env_path)
    return root


def portkey_client() -> AsyncOpenAI:
    load_root_env()
    api_key = os.getenv("PORTKEY_API_KEY")
    if not api_key:
        raise MissingModelKey(
            "PORTKEY_API_KEY is missing. Add it to the .env at the class folder root "
            "(/Users/jake/Desktop/AI Class/.env)."
        )
    base_url = os.getenv("PORTKEY_BASE_URL") or "https://api.portkey.ai/v1"
    return AsyncOpenAI(api_key=api_key, base_url=base_url)


def make_model() -> OpenAIChatModel:
    """Always gpt-6-luna through Portkey — ignore any other PORTKEY_MODEL."""
    return OpenAIChatModel(
        MODEL_NAME,
        provider=OpenAIProvider(openai_client=portkey_client()),
    )
