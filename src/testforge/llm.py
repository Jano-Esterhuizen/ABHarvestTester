"""Shared LLM configuration for all TestForge agents."""

import os

from crewai import LLM


def get_llm(model: str = "gpt-4o-mini") -> LLM:
    """Create an LLM instance configured for GitHub Models API."""
    return LLM(
        model=f"openai/{model}",
        api_key=os.environ.get("OPENAI_API_KEY") or os.environ.get("GITHUB_TOKEN"),
        base_url=os.environ.get("OPENAI_API_BASE") or "https://models.github.ai/inference",
    )
