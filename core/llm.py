"""
LLM Provider Abstraction
Routes requests to the appropriate LLM (local Ollama or cloud APIs)
based on task complexity and config.
"""
from __future__ import annotations

import os
from enum import Enum
from typing import Optional

import yaml
from langchain_core.language_models import BaseChatModel
from langchain_community.chat_models import ChatOllama
from loguru import logger


class TaskComplexity(Enum):
    SIMPLE = "simple"
    COMPLEX = "complex"


class LLMProvider:
    """Manages LLM instances and routes requests based on task complexity."""

    def __init__(self, config: dict):
        self.config = config
        self._models: dict[str, BaseChatModel] = {}

    def _get_ollama(self) -> BaseChatModel:
        if "ollama" not in self._models:
            cfg = self.config["ollama"]
            self._models["ollama"] = ChatOllama(
                base_url=cfg.get("base_url", "http://127.0.0.1:11434"),
                model=cfg.get("model", "qwen2.5:7b"),
                temperature=0.7,
            )
        return self._models["ollama"]

    def _get_openai(self) -> BaseChatModel:
        if "openai" not in self._models:
            from langchain_openai import ChatOpenAI

            cfg = self.config["openai"]
            os.environ.setdefault("OPENAI_API_KEY", cfg.get("api_key", ""))
            self._models["openai"] = ChatOpenAI(
                model=cfg.get("model", "gpt-4o-mini"),
                temperature=0.7,
            )
        return self._models["openai"]

    def _get_anthropic(self) -> BaseChatModel:
        if "anthropic" not in self._models:
            from langchain_community.chat_models import ChatAnthropic

            cfg = self.config["anthropic"]
            os.environ.setdefault("ANTHROPIC_API_KEY", cfg.get("api_key", ""))
            self._models["anthropic"] = ChatAnthropic(
                model=cfg.get("model", "claude-sonnet-4-5-20250929"),
                temperature=0.7,
            )
        return self._models["anthropic"]

    def get(self, provider: Optional[str] = None, complexity: TaskComplexity = TaskComplexity.SIMPLE) -> BaseChatModel:
        """
        Get an LLM instance.
        
        Args:
            provider: Explicit provider name ("ollama", "openai", "anthropic")
            complexity: If no provider specified, routes based on complexity config
        
        Returns:
            A LangChain chat model instance
        """
        if provider is None:
            routing = self.config.get("routing", {})
            if complexity == TaskComplexity.COMPLEX:
                provider = routing.get("complex_tasks", self.config.get("default_provider", "ollama"))
            else:
                provider = routing.get("simple_tasks", self.config.get("default_provider", "ollama"))

        provider_map = {
            "ollama": self._get_ollama,
            "openai": self._get_openai,
            "anthropic": self._get_anthropic,
        }

        if provider not in provider_map:
            logger.warning(f"Unknown provider '{provider}', falling back to ollama")
            provider = "ollama"

        logger.debug(f"Using LLM provider: {provider}")
        return provider_map[provider]()


def load_llm_provider(config_path: str = "config/config.yaml") -> LLMProvider:
    """Load LLM provider from config file."""
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return LLMProvider(config["llm"])
