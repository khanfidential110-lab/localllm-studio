"""
Inference Backend Abstract Base Class
======================================
Defines the interface that all inference backends must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Generator, Dict, Any, List, Optional
from enum import Enum


class BackendCapability(Enum):
    """Capabilities a backend may support."""
    STREAMING = "streaming"
    BATCH = "batch"
    EMBEDDINGS = "embeddings"
    VISION = "vision"
    FUNCTION_CALLING = "function_calling"


@dataclass
class GenerationConfig:
    """Configuration for text generation."""
    max_tokens: int = 2048
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    repeat_penalty: float = 1.1
    stop_sequences: List[str] = field(default_factory=list)
    stream: bool = True


@dataclass
class GenerationResult:
    """Result from a generation call."""
    text: str
    tokens_generated: int = 0
    tokens_per_second: float = 0.0
    prompt_tokens: int = 0
    finish_reason: str = "stop"  # stop, length, error


@dataclass
class ModelInfo:
    """Information about a loaded model."""
    name: str
    path: str
    size_gb: float
    context_length: int
    vocab_size: int
    quantization: Optional[str] = None
    parameters: Optional[str] = None  # e.g., "7B", "13B"


class InferenceBackend(ABC):
    """
    Abstract base class for inference backends.
    
    All backends (llama.cpp, MLX, Transformers, vLLM) must implement
    this interface to be usable by LocalLLM Studio.
    """
    
    def __init__(self):
        self._model = None
        self._tokenizer = None
        self._model_info: Optional[ModelInfo] = None
        self._is_loaded = False
    
    @property
    def name(self) -> str:
        """Return the backend name."""
        return self.__class__.__name__
    
    @property
    def is_loaded(self) -> bool:
        """Check if a model is currently loaded."""
        return self._is_loaded
    
    @property
    def model_info(self) -> Optional[ModelInfo]:
        """Get information about the loaded model."""
        return self._model_info
    
    @abstractmethod
    def get_capabilities(self) -> List[BackendCapability]:
        """
        Return list of capabilities this backend supports.
        
        Returns:
            List of BackendCapability enum values
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if this backend is available on the current system.
        
        Returns:
            True if the backend can be used, False otherwise
        """
        pass
    
    @abstractmethod
    def load_model(
        self,
        model_path: str,
        **kwargs
    ) -> ModelInfo:
        """
        Load a model from the specified path.
        
        Args:
            model_path: Path to model file or HuggingFace repo
            **kwargs: Backend-specific options (context length, GPU layers, etc.)
        
        Returns:
            ModelInfo about the loaded model
        
        Raises:
            FileNotFoundError: If model path doesn't exist
            MemoryError: If model is too large for available memory
            RuntimeError: For other loading errors
        """
        pass
    
    @abstractmethod
    def unload_model(self) -> None:
        """
        Unload the current model and free memory.
        """
        pass
    
    @abstractmethod
    def generate(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
    ) -> Generator[GenerationResult, None, None]:
        """
        Generate text from the given prompt.
        
        Args:
            prompt: The input text prompt
            config: Generation configuration (optional, uses defaults)
        
        Yields:
            GenerationResult objects with incremental text (if streaming)
            or a single result (if not streaming)
        
        Raises:
            RuntimeError: If no model is loaded
        """
        pass
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        config: Optional[GenerationConfig] = None,
    ) -> Generator[GenerationResult, None, None]:
        """
        Generate a chat response from conversation messages.
        
        Default implementation formats messages and calls generate().
        Backends may override for native chat template support.
        
        Args:
            messages: List of {"role": "user/assistant/system", "content": "..."}
            config: Generation configuration
        
        Yields:
            GenerationResult objects
        """
        # Default: format as simple chat
        prompt = self._format_messages(messages)
        yield from self.generate(prompt, config)
    
    def _format_messages(self, messages: List[Dict[str, str]]) -> str:
        """Format chat messages into a prompt string."""
        parts = []
        for msg in messages:
            role = msg.get("role", "user").capitalize()
            content = msg.get("content", "")
            parts.append(f"{role}: {content}")
        parts.append("Assistant:")
        return "\n".join(parts)
    
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in the given text.
        
        Args:
            text: Input text
        
        Returns:
            Number of tokens
        """
        pass
    
    def get_backend_info(self) -> Dict[str, Any]:
        """
        Get information about this backend.
        
        Returns:
            Dict with backend name, version, capabilities, etc.
        """
        return {
            "name": self.name,
            "capabilities": [c.value for c in self.get_capabilities()],
            "is_available": self.is_available(),
            "is_loaded": self.is_loaded,
            "model": self.model_info.name if self.model_info else None,
        }
