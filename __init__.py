#!/usr/bin/env python3
"""
LocalLLM Studio - Cross-Platform Local LLM Application
========================================================
A commercial-grade local LLM runner that works on all platforms
with support for models from 1B to 100B+ parameters.

Supports multiple inference backends:
- llama.cpp (Windows, Linux, macOS - CPU/CUDA/Metal)
- MLX (Apple Silicon only)
- Transformers (Universal fallback)
- vLLM (Linux + CUDA, high throughput)

Requirements:
    pip install llama-cpp-python flask huggingface-hub requests

Author: LocalLLM Studio Team
Date: December 2025
License: MIT
"""

__version__ = "1.0.0"
__app_name__ = "LocalLLM Studio"
