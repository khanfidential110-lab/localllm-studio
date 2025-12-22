"""
Model Library
==============
Curated list of recommended models with metadata.
"""

from dataclasses import dataclass
from typing import List, Optional
from enum import Enum


class ModelCategory(Enum):
    TINY = "tiny"        # 1-3B, runs on anything
    SMALL = "small"      # 7-8B, 8GB+ RAM
    MEDIUM = "medium"    # 13-14B, 16GB+ RAM
    LARGE = "large"      # 30-34B, 32GB+ RAM
    XL = "xl"            # 70B+, 64GB+ RAM
    XXL = "xxl"          # 100B+, multi-GPU


class ModelType(Enum):
    CHAT = "chat"
    INSTRUCT = "instruct"
    CODE = "code"
    REASONING = "reasoning"
    BASE = "base"


@dataclass
class ModelEntry:
    """A model in the library."""
    name: str
    repo_id: str
    description: str
    category: ModelCategory
    model_type: ModelType
    size_gb: float
    context_length: int
    parameters: str  # e.g., "7B", "70B"
    format: str  # e.g., "GGUF", "MLX", "SafeTensors"
    quantization: Optional[str] = None
    recommended: bool = False
    
    def fits_memory(self, available_gb: float) -> bool:
        """Check if model fits in available memory with headroom."""
        return self.size_gb <= available_gb * 0.85


# =============================================================================
# CURATED MODEL LIBRARY
# =============================================================================

GGUF_MODELS: List[ModelEntry] = [
    # === TINY (1-3B) ===
    ModelEntry(
        name="TinyLlama 1.1B",
        repo_id="TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF",
        description="Ultra-compact chat model, runs anywhere",
        category=ModelCategory.TINY,
        model_type=ModelType.CHAT,
        size_gb=0.6,
        context_length=2048,
        parameters="1.1B",
        format="GGUF",
        quantization="Q4_K_M",
    ),
    ModelEntry(
        name="Phi-3.5 Mini",
        repo_id="bartowski/Phi-3.5-mini-instruct-GGUF",
        description="Microsoft's compact powerhouse, excellent reasoning",
        category=ModelCategory.TINY,
        model_type=ModelType.INSTRUCT,
        size_gb=2.2,
        context_length=128000,
        parameters="3.8B",
        format="GGUF",
        quantization="Q4_K_M",
        recommended=True,
    ),
    ModelEntry(
        name="Qwen2.5 3B",
        repo_id="Qwen/Qwen2.5-3B-Instruct-GGUF",
        description="Alibaba's efficient multilingual model",
        category=ModelCategory.TINY,
        model_type=ModelType.INSTRUCT,
        size_gb=1.8,
        context_length=32768,
        parameters="3B",
        format="GGUF",
        quantization="Q4_K_M",
    ),
    
    # === SMALL (7-8B) ===
    ModelEntry(
        name="Llama 3.1 8B Instruct",
        repo_id="bartowski/Meta-Llama-3.1-8B-Instruct-GGUF",
        description="Meta's flagship small model, excellent all-rounder",
        category=ModelCategory.SMALL,
        model_type=ModelType.INSTRUCT,
        size_gb=4.7,
        context_length=131072,
        parameters="8B",
        format="GGUF",
        quantization="Q4_K_M",
        recommended=True,
    ),
    ModelEntry(
        name="Qwen3 8B",
        repo_id="Qwen/Qwen3-8B-GGUF",
        description="Best overall quality for 8GB systems",
        category=ModelCategory.SMALL,
        model_type=ModelType.CHAT,
        size_gb=4.5,
        context_length=32768,
        parameters="8B",
        format="GGUF",
        quantization="Q4_K_M",
        recommended=True,
    ),
    ModelEntry(
        name="Mistral 7B Instruct",
        repo_id="TheBloke/Mistral-7B-Instruct-v0.2-GGUF",
        description="Fast and capable, great for code",
        category=ModelCategory.SMALL,
        model_type=ModelType.INSTRUCT,
        size_gb=4.1,
        context_length=32768,
        parameters="7B",
        format="GGUF",
        quantization="Q4_K_M",
    ),
    ModelEntry(
        name="DeepSeek Coder 6.7B",
        repo_id="TheBloke/deepseek-coder-6.7B-instruct-GGUF",
        description="Specialized for coding tasks",
        category=ModelCategory.SMALL,
        model_type=ModelType.CODE,
        size_gb=3.8,
        context_length=16384,
        parameters="6.7B",
        format="GGUF",
        quantization="Q4_K_M",
    ),
    
    # === MEDIUM (13-14B) ===
    ModelEntry(
        name="Qwen2.5 14B Instruct",
        repo_id="Qwen/Qwen2.5-14B-Instruct-GGUF",
        description="Excellent balance of quality and speed",
        category=ModelCategory.MEDIUM,
        model_type=ModelType.INSTRUCT,
        size_gb=8.3,
        context_length=131072,
        parameters="14B",
        format="GGUF",
        quantization="Q4_K_M",
        recommended=True,
    ),
    ModelEntry(
        name="Llama 2 13B Chat",
        repo_id="TheBloke/Llama-2-13B-chat-GGUF",
        description="Proven reliable, good for chat",
        category=ModelCategory.MEDIUM,
        model_type=ModelType.CHAT,
        size_gb=7.4,
        context_length=4096,
        parameters="13B",
        format="GGUF",
        quantization="Q4_K_M",
    ),
    
    # === LARGE (30-34B) ===
    ModelEntry(
        name="DeepSeek 33B Instruct",
        repo_id="TheBloke/deepseek-llm-33b-instruct-GGUF",
        description="Strong reasoning and instruction following",
        category=ModelCategory.LARGE,
        model_type=ModelType.INSTRUCT,
        size_gb=19.0,
        context_length=4096,
        parameters="33B",
        format="GGUF",
        quantization="Q4_K_M",
    ),
    ModelEntry(
        name="CodeLlama 34B Instruct",
        repo_id="TheBloke/CodeLlama-34B-Instruct-GGUF",
        description="Meta's best coding model",
        category=ModelCategory.LARGE,
        model_type=ModelType.CODE,
        size_gb=19.5,
        context_length=16384,
        parameters="34B",
        format="GGUF",
        quantization="Q4_K_M",
    ),
    
    # === XL (70B+) ===
    ModelEntry(
        name="Llama 3.1 70B Instruct",
        repo_id="bartowski/Meta-Llama-3.1-70B-Instruct-GGUF",
        description="Meta's most capable open model",
        category=ModelCategory.XL,
        model_type=ModelType.INSTRUCT,
        size_gb=40.0,
        context_length=131072,
        parameters="70B",
        format="GGUF",
        quantization="Q4_K_M",
        recommended=True,
    ),
    ModelEntry(
        name="Qwen2.5 72B Instruct",
        repo_id="Qwen/Qwen2.5-72B-Instruct-GGUF",
        description="Alibaba's flagship, excellent at everything",
        category=ModelCategory.XL,
        model_type=ModelType.INSTRUCT,
        size_gb=42.0,
        context_length=131072,
        parameters="72B",
        format="GGUF",
        quantization="Q4_K_M",
    ),
    ModelEntry(
        name="DeepSeek R1 70B (Distilled)",
        repo_id="bartowski/DeepSeek-R1-Distill-Llama-70B-GGUF",
        description="Advanced reasoning capabilities",
        category=ModelCategory.XL,
        model_type=ModelType.REASONING,
        size_gb=40.0,
        context_length=32768,
        parameters="70B",
        format="GGUF",
        quantization="Q4_K_M",
    ),
]


def get_models_by_category(category: ModelCategory) -> List[ModelEntry]:
    """Get all models in a category."""
    return [m for m in GGUF_MODELS if m.category == category]


def get_recommended_models() -> List[ModelEntry]:
    """Get all recommended models."""
    return [m for m in GGUF_MODELS if m.recommended]


def get_models_that_fit(available_gb: float) -> List[ModelEntry]:
    """Get models that fit in available memory."""
    return [m for m in GGUF_MODELS if m.fits_memory(available_gb)]


def get_best_model_for_memory(available_gb: float) -> Optional[ModelEntry]:
    """Get the best (largest recommended) model that fits."""
    fitting = get_models_that_fit(available_gb)
    recommended = [m for m in fitting if m.recommended]
    
    if recommended:
        # Return largest recommended model that fits
        return max(recommended, key=lambda m: m.size_gb)
    elif fitting:
        # Return largest fitting model
        return max(fitting, key=lambda m: m.size_gb)
    else:
        # Return smallest model as fallback
        return min(GGUF_MODELS, key=lambda m: m.size_gb)


def search_models(query: str) -> List[ModelEntry]:
    """Search models by name or description."""
    query = query.lower()
    return [
        m for m in GGUF_MODELS
        if query in m.name.lower() or query in m.description.lower()
    ]
