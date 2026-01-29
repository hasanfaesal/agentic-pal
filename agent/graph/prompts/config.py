"""
Configuration for prompt mode selection.

This module provides a simple switch to toggle between:
1. "legacy" - Traditional string-based prompts with LangChain
2. "dspy" - DSPy signatures and modules for structured prompting

Usage:
    from agent.graph.prompts.config import PromptConfig, PromptMode
    
    # Check current mode
    if PromptConfig.mode == PromptMode.DSPY:
        # Use DSPy modules
        ...
    
    # Change mode
    PromptConfig.set_mode(PromptMode.LEGACY)
    
    # Or use environment variable:
    # export AGENTIC_PAL_PROMPT_MODE=dspy
"""

import os
from enum import Enum
from typing import Optional
import dspy


class PromptMode(str, Enum):
    """Available prompt modes."""
    LEGACY = "legacy"  # Traditional string prompts with LangChain
    DSPY = "dspy"      # DSPy signatures and modules


class PromptConfig:
    """
    Global configuration for prompt mode selection.
    
    This is a singleton-style configuration that can be changed at runtime.
    """
    
    _mode: PromptMode = PromptMode.LEGACY
    _dspy_lm: Optional[dspy.LM] = None
    _initialized: bool = False
    
    @classmethod
    def get_mode(cls) -> PromptMode:
        """Get the current prompt mode."""
        if not cls._initialized:
            cls._initialize_from_env()
        return cls._mode
    
    @classmethod
    def set_mode(cls, mode: PromptMode) -> None:
        """
        Set the prompt mode.
        
        Args:
            mode: The prompt mode to use
        """
        cls._mode = mode
        cls._initialized = True
    
    @classmethod
    def _initialize_from_env(cls) -> None:
        """Initialize mode from environment variable if set."""
        env_mode = os.environ.get("AGENTIC_PAL_PROMPT_MODE", "legacy").lower()
        if env_mode == "dspy":
            cls._mode = PromptMode.DSPY
        else:
            cls._mode = PromptMode.LEGACY
        cls._initialized = True
    
    @classmethod
    def is_dspy(cls) -> bool:
        """Check if using DSPy mode."""
        return cls.get_mode() == PromptMode.DSPY
    
    @classmethod
    def is_legacy(cls) -> bool:
        """Check if using legacy mode."""
        return cls.get_mode() == PromptMode.LEGACY
    
    @classmethod
    def configure_dspy(
        cls,
        model: str = "openai/gpt-4o-mini",
        api_key: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Configure DSPy with a language model.
        
        This must be called before using DSPy mode.
        
        Args:
            model: Model identifier (e.g., "openai/gpt-4o-mini", "anthropic/claude-3-sonnet")
            api_key: API key (defaults to environment variable)
            **kwargs: Additional arguments for dspy.LM
        """
        cls._dspy_lm = dspy.LM(model=model, api_key=api_key, **kwargs)
        dspy.configure(lm=cls._dspy_lm)
        cls._mode = PromptMode.DSPY
        cls._initialized = True
    
    @classmethod
    def configure_dspy_from_langchain(cls, langchain_llm) -> None:
        """
        Configure DSPy using an existing LangChain LLM.
        
        This allows reusing the same LLM configuration.
        
        Args:
            langchain_llm: A LangChain chat model instance
        """
        # Extract model info from LangChain LLM
        model_name = getattr(langchain_llm, "model_name", None) or getattr(langchain_llm, "model", "gpt-4o-mini")
        
        # Try to get API key from LangChain LLM
        api_key = getattr(langchain_llm, "api_key", None) or getattr(langchain_llm, "openai_api_key", None)
        
        # For Qwen models, use dashscope
        if "qwen" in model_name.lower():
            api_key = api_key or os.environ.get("DASHSCOPE_API_KEY")
            # DSPy doesn't natively support Qwen, so we'll use a compatible provider
            # or fall back to the model string as-is
            cls._dspy_lm = dspy.LM(
                model=f"dashscope/{model_name}",
                api_key=api_key
            )
        else:
            cls._dspy_lm = dspy.LM(model=model_name, api_key=api_key)
        
        dspy.configure(lm=cls._dspy_lm)
        cls._mode = PromptMode.DSPY
        cls._initialized = True
    
    @classmethod
    def get_dspy_lm(cls) -> Optional[dspy.LM]:
        """Get the configured DSPy language model."""
        return cls._dspy_lm
    
    @classmethod
    def reset(cls) -> None:
        """Reset configuration to defaults."""
        cls._mode = PromptMode.LEGACY
        cls._dspy_lm = None
        cls._initialized = False


# Convenience functions
def use_dspy() -> None:
    """Switch to DSPy mode."""
    PromptConfig.set_mode(PromptMode.DSPY)


def use_legacy() -> None:
    """Switch to legacy mode."""
    PromptConfig.set_mode(PromptMode.LEGACY)


def is_dspy_mode() -> bool:
    """Check if currently using DSPy mode."""
    return PromptConfig.is_dspy()


def is_legacy_mode() -> bool:
    """Check if currently using legacy mode."""
    return PromptConfig.is_legacy()
