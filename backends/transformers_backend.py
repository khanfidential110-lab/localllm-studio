"""
Transformers Backend
=====================
Universal fallback using HuggingFace Transformers.
Works on any platform with CPU or CUDA.
"""

import time
from typing import Generator, List, Optional

from .base import (
    InferenceBackend,
    BackendCapability,
    GenerationConfig,
    GenerationResult,
    ModelInfo,
)


class TransformersBackend(InferenceBackend):
    """
    HuggingFace Transformers backend.
    
    Features:
    - Universal compatibility (any platform)
    - Supports any HuggingFace model
    - bitsandbytes quantization (CUDA)
    - AutoGPTQ/AWQ support
    
    Note: Generally slower than llama.cpp or MLX,
    but provides the widest model compatibility.
    """
    
    def __init__(self):
        super().__init__()
        self._pipeline = None
        self._streamer = None
        self._device = "cpu"
    
    def get_capabilities(self) -> List[BackendCapability]:
        return [
            BackendCapability.STREAMING,
            BackendCapability.EMBEDDINGS,
        ]
    
    def is_available(self) -> bool:
        """Check if transformers is installed."""
        try:
            import transformers
            import torch
            return True
        except ImportError:
            return False
    
    def load_model(
        self,
        model_path: str,
        load_in_4bit: bool = False,
        load_in_8bit: bool = False,
        device_map: str = "auto",
        **kwargs
    ) -> ModelInfo:
        """
        Load a Transformers model.
        
        Args:
            model_path: HuggingFace repo or local path
            load_in_4bit: Use 4-bit quantization (requires bitsandbytes + CUDA)
            load_in_8bit: Use 8-bit quantization (requires bitsandbytes + CUDA)
            device_map: Device placement ("auto", "cuda", "cpu")
        """
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
            from transformers import TextIteratorStreamer
        except ImportError:
            raise ImportError(
                "transformers not installed. Install with:\n"
                "  pip install transformers torch\n"
                "For GPU: pip install transformers torch bitsandbytes accelerate"
            )
        
        print(f"[LOAD] Loading Transformers model: {model_path}")
        
        # Determine device
        if torch.cuda.is_available():
            self._device = "cuda"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            self._device = "mps"
        else:
            self._device = "cpu"
        
        print(f"   Device: {self._device}")
        
        # Load tokenizer
        self._tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        
        # Model loading kwargs
        model_kwargs = {
            "trust_remote_code": True,
        }
        
        if self._device == "cuda":
            model_kwargs["device_map"] = device_map
            if load_in_4bit:
                try:
                    from transformers import BitsAndBytesConfig
                    model_kwargs["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True)
                except ImportError:
                    print("[WARN] bitsandbytes not available, loading in fp16")
                    model_kwargs["torch_dtype"] = torch.float16
            elif load_in_8bit:
                try:
                    from transformers import BitsAndBytesConfig
                    model_kwargs["quantization_config"] = BitsAndBytesConfig(load_in_8bit=True)
                except ImportError:
                    print("[WARN] bitsandbytes not available, loading in fp16")
                    model_kwargs["torch_dtype"] = torch.float16
            else:
                model_kwargs["torch_dtype"] = torch.float16
        elif self._device == "mps":
            model_kwargs["torch_dtype"] = torch.float16
        
        try:
            self._model = AutoModelForCausalLM.from_pretrained(model_path, **model_kwargs)
            
            if self._device == "cpu":
                # Keep on CPU
                pass
            elif self._device == "mps":
                self._model = self._model.to("mps")
        except Exception as e:
            if "out of memory" in str(e).lower():
                raise MemoryError(f"Not enough memory: {e}")
            raise RuntimeError(f"Failed to load model: {e}")
        
        # Create pipeline for easier generation
        self._pipeline = pipeline(
            "text-generation",
            model=self._model,
            tokenizer=self._tokenizer,
        )
        
        self._is_loaded = True
        
        # Model info
        model_name = model_path.split("/")[-1] if "/" in model_path else model_path
        
        quant = None
        if load_in_4bit:
            quant = "4bit"
        elif load_in_8bit:
            quant = "8bit"
        
        self._model_info = ModelInfo(
            name=model_name,
            path=model_path,
            size_gb=0,
            context_length=getattr(self._tokenizer, 'model_max_length', 4096),
            vocab_size=len(self._tokenizer),
            quantization=quant,
        )
        
        print(f"[OK] Model loaded on {self._device}!")
        return self._model_info
    
    def unload_model(self) -> None:
        """Unload and free memory."""
        if self._model is not None:
            del self._model
            self._model = None
        if self._tokenizer is not None:
            del self._tokenizer
            self._tokenizer = None
        if self._pipeline is not None:
            del self._pipeline
            self._pipeline = None
        
        self._is_loaded = False
        self._model_info = None
        
        # Free CUDA memory
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except:
            pass
        
        import gc
        gc.collect()
    
    def generate(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
    ) -> Generator[GenerationResult, None, None]:
        """Generate text."""
        if not self._is_loaded:
            raise RuntimeError("No model loaded.")
        
        if config is None:
            config = GenerationConfig()
        
        start_time = time.perf_counter()
        
        try:
            if config.stream:
                # Streaming with TextIteratorStreamer
                from transformers import TextIteratorStreamer
                from threading import Thread
                
                streamer = TextIteratorStreamer(
                    self._tokenizer,
                    skip_prompt=True,
                    skip_special_tokens=True,
                )
                
                inputs = self._tokenizer(prompt, return_tensors="pt")
                if self._device != "cpu":
                    inputs = {k: v.to(self._device) for k, v in inputs.items()}
                
                generation_kwargs = {
                    **inputs,
                    "max_new_tokens": config.max_tokens,
                    "temperature": config.temperature,
                    "top_p": config.top_p,
                    "top_k": config.top_k,
                    "do_sample": config.temperature > 0,
                    "streamer": streamer,
                }
                
                thread = Thread(target=self._model.generate, kwargs=generation_kwargs)
                thread.start()
                
                tokens_generated = 0
                for text in streamer:
                    tokens_generated += 1
                    elapsed = time.perf_counter() - start_time
                    tps = tokens_generated / elapsed if elapsed > 0 else 0
                    
                    yield GenerationResult(
                        text=text,
                        tokens_generated=tokens_generated,
                        tokens_per_second=round(tps, 1),
                        finish_reason="generating",
                    )
                
                thread.join()
                
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
                outputs = self._pipeline(
                    prompt,
                    max_new_tokens=config.max_tokens,
                    temperature=config.temperature,
                    top_p=config.top_p,
                    do_sample=config.temperature > 0,
                    return_full_text=False,
                )
                
                text = outputs[0]["generated_text"]
                elapsed = time.perf_counter() - start_time
                tokens = len(self._tokenizer.encode(text))
                tps = tokens / elapsed if elapsed > 0 else 0
                
                yield GenerationResult(
                    text=text,
                    tokens_generated=tokens,
                    tokens_per_second=round(tps, 1),
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
        """Chat with proper template."""
        if not self._is_loaded:
            raise RuntimeError("No model loaded.")
        
        try:
            prompt = self._tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        except:
            prompt = self._format_messages(messages)
        
        yield from self.generate(prompt, config)
    
    def count_tokens(self, text: str) -> int:
        """Count tokens."""
        if not self._is_loaded:
            raise RuntimeError("No model loaded.")
        return len(self._tokenizer.encode(text))
