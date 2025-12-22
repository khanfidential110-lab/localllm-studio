"""
MLX Backend for Apple Silicon
==============================
Optimized inference for M1/M2/M3 Macs using Apple's MLX framework.
"""

import time
from pathlib import Path
from typing import Generator, List, Optional

from .base import (
    InferenceBackend,
    BackendCapability,
    GenerationConfig,
    GenerationResult,
    ModelInfo,
)


class MLXBackend(InferenceBackend):
    """
    MLX backend for Apple Silicon Macs.
    
    Features:
    - Native Apple Silicon optimization
    - Unified memory architecture
    - Fast 4-bit and 8-bit quantization
    - Stream generation support
    """
    
    def __init__(self):
        super().__init__()
        self._generate_func = None
        self._stream_func = None
    
    def get_capabilities(self) -> List[BackendCapability]:
        return [
            BackendCapability.STREAMING,
        ]
    
    def is_available(self) -> bool:
        """Check if MLX is available (Apple Silicon only)."""
        try:
            import mlx.core as mx
            import mlx_lm
            # Check if Metal is available
            return True
        except ImportError:
            return False
        except Exception:
            return False
    
    def load_model(
        self,
        model_path: str,
        **kwargs
    ) -> ModelInfo:
        """
        Load an MLX model.
        
        Args:
            model_path: HuggingFace repo (e.g., "mlx-community/Llama-3.1-8B-Instruct-4bit")
        """
        try:
            from mlx_lm import load, stream_generate, generate
        except ImportError:
            raise ImportError(
                "mlx-lm not installed. Install with:\n"
                "  pip install mlx-lm\n"
                "Note: Only works on Apple Silicon Macs."
            )
        
        print(f"📥 Loading MLX model: {model_path}")
        
        try:
            self._model, self._tokenizer = load(model_path)
            self._stream_func = stream_generate
            self._generate_func = generate
        except Exception as e:
            if "out of memory" in str(e).lower():
                raise MemoryError(f"Not enough memory: {e}")
            raise RuntimeError(f"Failed to load model: {e}")
        
        self._is_loaded = True
        
        # Extract model info
        model_name = model_path.split("/")[-1] if "/" in model_path else model_path
        
        # Detect quantization
        quant = None
        for q in ["4bit", "8bit", "fp16"]:
            if q in model_name.lower():
                quant = q.upper()
                break
        
        # Detect parameters
        params = None
        for p in ["1B", "3B", "7B", "8B", "13B", "14B", "70B", "72B"]:
            if p.lower() in model_name.lower():
                params = p
                break
        
        self._model_info = ModelInfo(
            name=model_name,
            path=model_path,
            size_gb=0,  # MLX manages memory dynamically
            context_length=4096,
            vocab_size=self._tokenizer.vocab_size if hasattr(self._tokenizer, 'vocab_size') else 0,
            quantization=quant,
            parameters=params,
        )
        
        print(f"✅ Model loaded!")
        return self._model_info
    
    def unload_model(self) -> None:
        """Unload model and free memory."""
        if self._model is not None:
            del self._model
            self._model = None
        if self._tokenizer is not None:
            del self._tokenizer
            self._tokenizer = None
        
        self._is_loaded = False
        self._model_info = None
        
        # Clear MLX cache
        try:
            import mlx.core as mx
            mx.metal.clear_cache()
        except:
            pass
        
        import gc
        gc.collect()
    
    def generate(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
    ) -> Generator[GenerationResult, None, None]:
        """Generate text with MLX."""
        if not self._is_loaded:
            raise RuntimeError("No model loaded.")
        
        if config is None:
            config = GenerationConfig()
        
        start_time = time.perf_counter()
        tokens_generated = 0
        full_text = ""
        
        try:
            if config.stream:
                # Streaming generation
                for response in self._stream_func(
                    model=self._model,
                    tokenizer=self._tokenizer,
                    prompt=prompt,
                    max_tokens=config.max_tokens,
                    temp=config.temperature,
                    top_p=config.top_p,
                ):
                    tokens_generated += 1
                    full_text += response.text
                    
                    elapsed = time.perf_counter() - start_time
                    tps = tokens_generated / elapsed if elapsed > 0 else 0
                    
                    yield GenerationResult(
                        text=response.text,
                        tokens_generated=tokens_generated,
                        tokens_per_second=round(tps, 1),
                        finish_reason="generating",
                    )
                
                # Final result
                elapsed = time.perf_counter() - start_time
                tps = tokens_generated / elapsed if elapsed > 0 else 0
                yield GenerationResult(
                    text="",
                    tokens_generated=tokens_generated,
                    tokens_per_second=round(tps, 1),
                    finish_reason="stop",
                )
            else:
                # Non-streaming
                result = self._generate_func(
                    model=self._model,
                    tokenizer=self._tokenizer,
                    prompt=prompt,
                    max_tokens=config.max_tokens,
                    temp=config.temperature,
                    top_p=config.top_p,
                )
                
                elapsed = time.perf_counter() - start_time
                
                yield GenerationResult(
                    text=result,
                    tokens_generated=len(self._tokenizer.encode(result)),
                    tokens_per_second=0,
                    finish_reason="stop",
                )
                
        except Exception as e:
            yield GenerationResult(
                text=f"Error: {str(e)}",
                finish_reason="error",
            )
    
    def chat(
        self,
        messages: List[dict],
        config: Optional[GenerationConfig] = None,
    ) -> Generator[GenerationResult, None, None]:
        """Generate chat response using chat template."""
        if not self._is_loaded:
            raise RuntimeError("No model loaded.")
        
        # Use tokenizer's chat template if available
        try:
            prompt = self._tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        except:
            # Fallback to simple format
            prompt = self._format_messages(messages)
        
        yield from self.generate(prompt, config)
    
    def count_tokens(self, text: str) -> int:
        """Count tokens."""
        if not self._is_loaded:
            raise RuntimeError("No model loaded.")
        return len(self._tokenizer.encode(text))
