"""
llama.cpp Backend
==================
Cross-platform inference using llama-cpp-python.
Supports GGUF models on Windows, Linux, and macOS.
"""

import os
import time
import threading
from pathlib import Path
from typing import Generator, Dict, Any, List, Optional

from .base import (
    InferenceBackend,
    BackendCapability,
    GenerationConfig,
    GenerationResult,
    ModelInfo,
)


class LlamaCppBackend(InferenceBackend):
    """
    llama.cpp backend via llama-cpp-python.
    
    Features:
    - Cross-platform: Windows, Linux, macOS
    - Hardware acceleration: CUDA, Metal, OpenCL, CPU
    - Format support: GGUF (Q2-Q8, F16)
    - Low memory footprint with quantization
    """
    
    def __init__(self):
        super().__init__()
        self._llm = None
        self._context_length = 4096
        self._stop_event = threading.Event()
    
    def get_capabilities(self) -> List[BackendCapability]:
        return [
            BackendCapability.STREAMING,
            BackendCapability.BATCH,
        ]
    
    def is_available(self) -> bool:
        """Check if llama-cpp-python is installed."""
        try:
            import llama_cpp
            return True
        except ImportError:
            return False
    
    def is_model_cached(self, repo_id: str) -> bool:
        """Check if a model is already cached locally."""
        try:
            from huggingface_hub import scan_cache_dir
            
            # Fast check: scan cache for repo
            hf_cache_info = scan_cache_dir()
            for repo in hf_cache_info.repos:
                if repo.repo_id == repo_id:
                    # Check if any GGUF file exists in this repo
                    for revision in repo.revisions:
                        for file in revision.files:
                            if file.file_name.endswith(".gguf"):
                                return True
            return False
        except Exception:
            return False

    def load_model(
        self,
        model_path: str,
        n_ctx: int = 4096,
        n_gpu_layers: int = -1,  # -1 = auto
        n_threads: Optional[int] = None,
        verbose: bool = False,
        progress_callback: Optional[callable] = None,
        **kwargs
    ) -> ModelInfo:
        """
        Load a GGUF model.
        
        Args:
            model_path: Path to .gguf file or HuggingFace repo
            n_ctx: Context length
            n_gpu_layers: GPU layers
            n_threads: CPU threads
            verbose: Print loading progress
            progress_callback: Optional func(status: str, progress: float)
        """
        try:
            from llama_cpp import Llama
        except ImportError:
            raise ImportError("llama-cpp-python not installed.")
        
        # Handle HuggingFace repo paths
        if "/" in model_path and not os.path.exists(model_path):
            if progress_callback:
                progress_callback("Finding model file...", 0.1)
            
            # Check if we need to download
            is_cached = self.is_model_cached(model_path)
            if not is_cached and progress_callback:
                progress_callback("Downloading model (this may take a while)...", 0.2)
            
            model_path = self._download_from_hf(model_path, progress_callback)
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found: {model_path}")
        
        # Get file size
        file_size = os.path.getsize(model_path) / (1024 ** 3)
        
        if progress_callback:
            progress_callback(f"Loading {file_size:.1f}GB into memory...", 0.8)
        
        # Auto-detect threads
        if n_threads is None:
            n_threads = min(os.cpu_count() or 4, 8)
        
        print(f"📥 Loading model: {model_path}")
        
        try:
            self._llm = Llama(
                model_path=model_path,
                n_ctx=n_ctx,
                n_gpu_layers=n_gpu_layers,
                n_threads=n_threads,
                verbose=verbose,
                **kwargs
            )
        except Exception as e:
            if "out of memory" in str(e).lower() or "cuda" in str(e).lower():
                raise MemoryError(f"Not enough memory to load model: {e}")
            raise RuntimeError(f"Failed to load model: {e}")
        
        self._context_length = n_ctx
        self._is_loaded = True
        
        # Extract model info
        model_name = Path(model_path).stem
        
        # Try to detect quantization from filename
        quant = None
        for q in ["Q2", "Q3", "Q4", "Q5", "Q6", "Q8", "F16", "F32"]:
            if q.lower() in model_name.lower():
                quant = q
                break
        
        # Try to detect parameter count
        params = None
        for p in ["1B", "3B", "7B", "8B", "13B", "14B", "30B", "33B", "34B", "70B", "72B"]:
            if p.lower() in model_name.lower():
                params = p
                break
        
        self._model_info = ModelInfo(
            name=model_name,
            path=model_path,
            size_gb=round(file_size, 2),
            context_length=n_ctx,
            vocab_size=self._llm.n_vocab(),
            quantization=quant,
            parameters=params,
        )
        
        if progress_callback:
            progress_callback("Ready", 1.0)
            
        print(f"✅ Model loaded! ({file_size:.1f} GB)")
        
        return self._model_info
    
    def cancel_loading(self):
        """Cancel the current loading/downloading operation."""
        if hasattr(self, '_current_process') and self._current_process:
            print("🛑 Cancelling download process...")
            self._current_process.kill()
            self._current_process = None
            
    def _download_from_hf(self, repo_id: str, progress_callback: Optional[callable] = None) -> str:
        """Download a GGUF model from HuggingFace with retry logic."""
        import time as time_module
        import traceback
        
        # We need to find the filename first to download specifically
        try:
            from huggingface_hub import list_repo_files, hf_hub_download
        except ImportError:
            raise ImportError("huggingface-hub not installed.")

        print(f"🔍 Searching for GGUF files in {repo_id}...")
        if progress_callback:
            progress_callback("Finding optimal model file...", 0.1)
        
        max_retries = 3
        retry_delay = 2  # seconds
        last_error = None
        
        for attempt in range(max_retries):
            try:
                print(f"📡 Attempt {attempt + 1}: Fetching file list from HuggingFace...")
                
                # Get file list
                files = list_repo_files(repo_id)
                gguf_files = [f for f in files if f.endswith(".gguf")]
                
                print(f"✅ Found {len(gguf_files)} GGUF files")
                
                if not gguf_files:
                    raise FileNotFoundError(f"No GGUF files found in {repo_id}")
                
                # Prefer Q4_K_M or similar mid-quality quantization
                preferred = None
                for pattern in ["Q4_K_M", "Q4_K_S", "Q5_K_M", "Q4_0", "Q5_0"]:
                    for f in gguf_files:
                        if pattern.lower() in f.lower():
                            preferred = f
                            break
                    if preferred:
                        break
                
                gguf_file = preferred or gguf_files[0]
                
                print(f"📥 Downloading: {gguf_file} (attempt {attempt + 1}/{max_retries})")
                if progress_callback:
                    progress_callback(f"Downloading {gguf_file}...", 0.2)
                
                # Direct download with resume support
                local_path = hf_hub_download(
                    repo_id=repo_id, 
                    filename=gguf_file,
                    resume_download=True
                )
                print(f"✅ Download complete: {local_path}")
                return local_path
                
            except Exception as e:
                last_error = e
                error_type = type(e).__name__
                error_msg = str(e)
                print(f"❌ Error ({error_type}): {error_msg}")
                print(f"   Full traceback:\n{traceback.format_exc()}")
                
                # Check if this is a retryable error
                retryable = any(term in error_type.lower() or term in error_msg.lower() 
                               for term in ['connection', 'timeout', 'network', 'ssl', 'socket'])
                
                if retryable and attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    print(f"⚠️ Retrying in {wait_time}s...")
                    if progress_callback:
                        progress_callback(f"Connection error, retrying in {wait_time}s...", 0.1)
                    time_module.sleep(wait_time)
                elif isinstance(e, (InterruptedError, FileNotFoundError)):
                    raise e
                else:
                    # Non-retryable or out of retries
                    raise RuntimeError(f"Download failed ({error_type}): {error_msg}")
    
    def unload_model(self) -> None:
        """Unload the model and free memory."""
        if self._llm is not None:
            del self._llm
            self._llm = None
        self._model_info = None
        self._is_loaded = False
        
        # Try to free GPU memory
        try:
            import gc
            gc.collect()
        except:
            pass
    
    def generate(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
    ) -> Generator[GenerationResult, None, None]:
        """Generate text with streaming support."""
        if not self._is_loaded or self._llm is None:
            raise RuntimeError("No model loaded. Call load_model() first.")
        
        if config is None:
            config = GenerationConfig()
        
        start_time = time.perf_counter()
        tokens_generated = 0
        full_text = ""
        
        try:
            if config.stream:
                # Streaming generation
                stream = self._llm(
                    prompt,
                    max_tokens=config.max_tokens,
                    temperature=config.temperature,
                    top_p=config.top_p,
                    top_k=config.top_k,
                    repeat_penalty=config.repeat_penalty,
                    stop=config.stop_sequences or None,
                    stream=True,
                )
                
                for output in stream:
                    token_text = output["choices"][0]["text"]
                    full_text += token_text
                    tokens_generated += 1
                    
                    elapsed = time.perf_counter() - start_time
                    tps = tokens_generated / elapsed if elapsed > 0 else 0
                    
                    finish_reason = output["choices"][0].get("finish_reason", "")
                    
                    yield GenerationResult(
                        text=token_text,
                        tokens_generated=tokens_generated,
                        tokens_per_second=round(tps, 1),
                        finish_reason=finish_reason or "generating",
                    )
            else:
                # Non-streaming generation
                output = self._llm(
                    prompt,
                    max_tokens=config.max_tokens,
                    temperature=config.temperature,
                    top_p=config.top_p,
                    top_k=config.top_k,
                    repeat_penalty=config.repeat_penalty,
                    stop=config.stop_sequences or None,
                    stream=False,
                )
                
                full_text = output["choices"][0]["text"]
                tokens_generated = output["usage"]["completion_tokens"]
                elapsed = time.perf_counter() - start_time
                tps = tokens_generated / elapsed if elapsed > 0 else 0
                
                yield GenerationResult(
                    text=full_text,
                    tokens_generated=tokens_generated,
                    tokens_per_second=round(tps, 1),
                    prompt_tokens=output["usage"]["prompt_tokens"],
                    finish_reason=output["choices"][0].get("finish_reason", "stop"),
                )
                
        except Exception as e:
            yield GenerationResult(
                text=f"Error: {str(e)}",
                tokens_generated=tokens_generated,
                finish_reason="error",
            )
    
    def stop_generation(self):
        """Signal to stop current generation."""
        self._stop_event.set()

    def chat(
        self,
        messages: List[Dict[str, str]],
        config: Optional[GenerationConfig] = None,
    ) -> Generator[GenerationResult, None, None]:
        """Generate chat response with proper chat template."""
        if not self._is_loaded or self._llm is None:
            raise RuntimeError("No model loaded.")
        
        if config is None:
            config = GenerationConfig()
            
        # Clear stop event at start of generation
        self._stop_event.clear()
        
        start_time = time.perf_counter()
        tokens_generated = 0
        full_text = ""
        
        try:
            if config.stream:
                stream = self._llm.create_chat_completion(
                    messages=messages,
                    max_tokens=config.max_tokens,
                    temperature=config.temperature,
                    top_p=config.top_p,
                    top_k=config.top_k,
                    repeat_penalty=config.repeat_penalty,
                    stop=config.stop_sequences or None,
                    stream=True,
                )
                
                for output in stream:
                    # Check for cancellation
                    if self._stop_event.is_set():
                        yield GenerationResult(
                            text="",
                            tokens_generated=tokens_generated,
                            finish_reason="stop",
                        )
                        return

                    delta = output["choices"][0].get("delta", {})
                    token_text = delta.get("content", "")
                    
                    if token_text:
                        full_text += token_text
                        tokens_generated += 1
                        
                        elapsed = time.perf_counter() - start_time
                        tps = tokens_generated / elapsed if elapsed > 0 else 0
                        
                        yield GenerationResult(
                            text=token_text,
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
                # Non-streaming (can't easily interrupt internal C++ loop, but we can check before)
                if self._stop_event.is_set():
                    return

                output = self._llm.create_chat_completion(
                    messages=messages,
                    max_tokens=config.max_tokens,
                    temperature=config.temperature,
                    top_p=config.top_p,
                    stream=False,
                )
                
                full_text = output["choices"][0]["message"]["content"]
                tokens_generated = output["usage"]["completion_tokens"]
                elapsed = time.perf_counter() - start_time
                tps = tokens_generated / elapsed if elapsed > 0 else 0
                
                yield GenerationResult(
                    text=full_text,
                    tokens_generated=tokens_generated,
                    tokens_per_second=round(tps, 1),
                    prompt_tokens=output["usage"]["prompt_tokens"],
                    finish_reason=output["choices"][0].get("finish_reason", "stop"),
                )
                
        except Exception as e:
            yield GenerationResult(
                text=f"Error: {str(e)}",
                finish_reason="error",
            )
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if not self._is_loaded or self._llm is None:
            raise RuntimeError("No model loaded.")
        return len(self._llm.tokenize(text.encode()))
