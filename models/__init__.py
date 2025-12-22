"""Models package."""
from .library import (
    ModelEntry,
    ModelCategory,
    ModelType,
    GGUF_MODELS,
    get_models_by_category,
    get_recommended_models,
    get_models_that_fit,
    get_best_model_for_memory,
    search_models,
)
