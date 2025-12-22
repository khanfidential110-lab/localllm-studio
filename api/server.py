"""
OpenAI-Compatible API Server
=============================
Provides /v1/chat/completions and other OpenAI-compatible endpoints.
"""

import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Generator

try:
    from flask import Flask, request, Response, jsonify
except ImportError:
    Flask = None

from ..backends import LlamaCppBackend, GenerationConfig, GenerationResult
from ..backends.base import InferenceBackend
from ..models import GGUF_MODELS, get_models_that_fit, get_best_model_for_memory
from ..utils import detect_hardware


class APIServer:
    """
    OpenAI-compatible API server.
    
    Endpoints:
        POST /v1/chat/completions - Chat completions (streaming supported)
        POST /v1/completions - Text completions
        GET  /v1/models - List available models
        GET  /health - Health check
    """
    
    def __init__(self, backend: Optional[InferenceBackend] = None):
        if Flask is None:
            raise ImportError("Flask not installed. pip install flask")
        
        self.app = Flask(__name__)
        self.backend = backend or LlamaCppBackend()
        self.hardware = detect_hardware()
        self._setup_routes()
    
    def _setup_routes(self):
        """Set up API routes."""
        
        @self.app.route('/health', methods=['GET'])
        def health():
            return jsonify({
                "status": "healthy",
                "model_loaded": self.backend.is_loaded,
                "model": self.backend.model_info.name if self.backend.model_info else None,
            })
        
        @self.app.route('/v1/models', methods=['GET'])
        def list_models():
            """List available models (OpenAI format)."""
            models = []
            
            # Add currently loaded model
            if self.backend.is_loaded and self.backend.model_info:
                models.append({
                    "id": self.backend.model_info.name,
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "local",
                })
            
            # Add library models
            for m in GGUF_MODELS:
                models.append({
                    "id": m.repo_id,
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "huggingface",
                    "metadata": {
                        "name": m.name,
                        "parameters": m.parameters,
                        "size_gb": m.size_gb,
                        "context_length": m.context_length,
                    }
                })
            
            return jsonify({
                "object": "list",
                "data": models,
            })
        
        @self.app.route('/v1/chat/completions', methods=['POST'])
        def chat_completions():
            """
            Chat completions endpoint (OpenAI compatible).
            
            Request body:
                {
                    "model": "model-name",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "stream": true/false,
                    "temperature": 0.7,
                    "max_tokens": 2048,
                    ...
                }
            """
            if not self.backend.is_loaded:
                return jsonify({
                    "error": {
                        "message": "No model loaded. Use /load endpoint first.",
                        "type": "invalid_request_error",
                        "code": "model_not_loaded"
                    }
                }), 400
            
            data = request.json
            messages = data.get("messages", [])
            stream = data.get("stream", False)
            
            # Build generation config
            config = GenerationConfig(
                max_tokens=data.get("max_tokens", 2048),
                temperature=data.get("temperature", 0.7),
                top_p=data.get("top_p", 0.9),
                stream=stream,
                stop_sequences=data.get("stop", []),
            )
            
            request_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
            created = int(time.time())
            model_name = self.backend.model_info.name
            
            if stream:
                return Response(
                    self._stream_chat_response(messages, config, request_id, created, model_name),
                    mimetype='text/event-stream',
                    headers={
                        'Cache-Control': 'no-cache',
                        'X-Accel-Buffering': 'no',
                    }
                )
            else:
                return self._sync_chat_response(messages, config, request_id, created, model_name)
        
        @self.app.route('/v1/completions', methods=['POST'])
        def completions():
            """Text completions endpoint (OpenAI compatible)."""
            if not self.backend.is_loaded:
                return jsonify({"error": {"message": "No model loaded"}}), 400
            
            data = request.json
            prompt = data.get("prompt", "")
            stream = data.get("stream", False)
            
            config = GenerationConfig(
                max_tokens=data.get("max_tokens", 2048),
                temperature=data.get("temperature", 0.7),
                top_p=data.get("top_p", 0.9),
                stream=stream,
                stop_sequences=data.get("stop", []),
            )
            
            request_id = f"cmpl-{uuid.uuid4().hex[:8]}"
            created = int(time.time())
            model_name = self.backend.model_info.name
            
            if stream:
                return Response(
                    self._stream_completion_response(prompt, config, request_id, created, model_name),
                    mimetype='text/event-stream',
                )
            else:
                return self._sync_completion_response(prompt, config, request_id, created, model_name)
        
        @self.app.route('/load', methods=['POST'])
        def load_model():
            """Load a model endpoint (non-standard, for convenience)."""
            data = request.json
            model_path = data.get("model")
            
            if not model_path:
                return jsonify({"error": "model path required"}), 400
            
            try:
                # Unload current model
                if self.backend.is_loaded:
                    self.backend.unload_model()
                
                # Load new model
                info = self.backend.load_model(
                    model_path,
                    n_ctx=data.get("context_length", 4096),
                    n_gpu_layers=data.get("gpu_layers", -1),
                )
                
                return jsonify({
                    "success": True,
                    "model": info.name,
                    "size_gb": info.size_gb,
                    "context_length": info.context_length,
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/unload', methods=['POST'])
        def unload_model():
            """Unload current model."""
            self.backend.unload_model()
            return jsonify({"success": True})
        
        @self.app.route('/hardware', methods=['GET'])
        def get_hardware():
            """Get hardware information."""
            return jsonify(self.hardware.to_dict())
    
    def _stream_chat_response(
        self, 
        messages: List[Dict], 
        config: GenerationConfig, 
        request_id: str,
        created: int,
        model: str
    ) -> Generator[str, None, None]:
        """Generate streaming chat response in SSE format."""
        try:
            for result in self.backend.chat(messages, config):
                if result.text:
                    chunk = {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {"content": result.text},
                            "finish_reason": None,
                        }]
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
                
                if result.finish_reason in ("stop", "length"):
                    final_chunk = {
                        "id": request_id,
                        "object": "chat.completion.chunk", 
                        "created": created,
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "finish_reason": result.finish_reason,
                        }]
                    }
                    yield f"data: {json.dumps(final_chunk)}\n\n"
            
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            error = {"error": {"message": str(e)}}
            yield f"data: {json.dumps(error)}\n\n"
    
    def _sync_chat_response(
        self,
        messages: List[Dict],
        config: GenerationConfig,
        request_id: str,
        created: int,
        model: str
    ) -> Response:
        """Generate synchronous chat response."""
        full_text = ""
        tokens = 0
        prompt_tokens = 0
        finish_reason = "stop"
        
        config.stream = False
        
        for result in self.backend.chat(messages, config):
            full_text += result.text
            tokens = result.tokens_generated
            prompt_tokens = result.prompt_tokens
            finish_reason = result.finish_reason
        
        return jsonify({
            "id": request_id,
            "object": "chat.completion",
            "created": created,
            "model": model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": full_text,
                },
                "finish_reason": finish_reason,
            }],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": tokens,
                "total_tokens": prompt_tokens + tokens,
            }
        })
    
    def _stream_completion_response(
        self,
        prompt: str,
        config: GenerationConfig,
        request_id: str,
        created: int,
        model: str
    ) -> Generator[str, None, None]:
        """Generate streaming completion response."""
        for result in self.backend.generate(prompt, config):
            if result.text:
                chunk = {
                    "id": request_id,
                    "object": "text_completion",
                    "created": created,
                    "model": model,
                    "choices": [{
                        "text": result.text,
                        "index": 0,
                        "finish_reason": None,
                    }]
                }
                yield f"data: {json.dumps(chunk)}\n\n"
        
        yield "data: [DONE]\n\n"
    
    def _sync_completion_response(
        self,
        prompt: str,
        config: GenerationConfig,
        request_id: str,
        created: int,
        model: str
    ) -> Response:
        """Generate synchronous completion response."""
        full_text = ""
        tokens = 0
        
        config.stream = False
        
        for result in self.backend.generate(prompt, config):
            full_text += result.text
            tokens = result.tokens_generated
        
        return jsonify({
            "id": request_id,
            "object": "text_completion",
            "created": created,
            "model": model,
            "choices": [{
                "text": full_text,
                "index": 0,
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": tokens,
                "total_tokens": tokens,
            }
        })
    
    def run(self, host: str = "0.0.0.0", port: int = 8000, debug: bool = False):
        """Run the API server."""
        print(f"\n{'=' * 60}")
        print("🚀 LocalLLM Studio API Server")
        print(f"{'=' * 60}")
        print(f"\n📡 API: http://{host}:{port}")
        print(f"   • POST /v1/chat/completions")
        print(f"   • POST /v1/completions")
        print(f"   • GET  /v1/models")
        print(f"   • POST /load")
        print(f"   • GET  /health")
        print(f"\n🔧 OpenAI SDK compatible:")
        print(f'   client = OpenAI(base_url="http://localhost:{port}/v1", api_key="local")')
        print(f"\nPress Ctrl+C to stop\n")
        
        self.app.run(host=host, port=port, debug=debug, threaded=True)


def create_api_server(backend: Optional[InferenceBackend] = None) -> APIServer:
    """Create and return an API server instance."""
    return APIServer(backend)
