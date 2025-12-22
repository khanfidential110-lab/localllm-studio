#!/usr/bin/env python3
"""
LocalLLM Studio - Cross-Platform Local LLM Application
========================================================
A commercial-grade local LLM runner for Windows, Linux, and macOS.

Usage:
    python -m localllm_studio                    # Interactive CLI
    python -m localllm_studio --web              # Web UI
    python -m localllm_studio --api              # OpenAI-compatible API server
    python -m localllm_studio --api --port 8000  # API on custom port

Requirements:
    pip install llama-cpp-python flask huggingface-hub

For GPU acceleration:
    - NVIDIA: pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121
    - Apple Metal: Automatically enabled on macOS
"""

import argparse
import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from localllm_studio import __version__, __app_name__
from localllm_studio.utils import detect_hardware, print_hardware_info
from localllm_studio.backends import LlamaCppBackend, GenerationConfig
from localllm_studio.models import GGUF_MODELS, get_models_that_fit, get_best_model_for_memory


def print_banner():
    """Print application banner."""
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   🚀 LocalLLM Studio                                             ║
║   ─────────────────────────────────────────────────────────────── ║
║   Cross-Platform Local LLM Application                           ║
║   Version: {version:10}                                           ║
║                                                                   ║
║   Supported Platforms: Windows · Linux · macOS                   ║
║   Backends: llama.cpp (CUDA/Metal/CPU)                           ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
""".format(version=__version__))


def select_model_interactive(hw):
    """Interactive model selection."""
    available_gb = hw.available_ram_gb
    if hw.gpu.vram_gb > 0:
        available_gb = max(available_gb, hw.gpu.vram_gb)
    
    fitting_models = get_models_that_fit(available_gb)
    best_model = get_best_model_for_memory(available_gb)
    
    print("\n📦 MODEL SELECTION")
    print("=" * 60)
    print(f"Available Memory: {available_gb:.1f} GB")
    print(f"Recommended: {best_model.name} ({best_model.size_gb:.1f} GB)")
    print("-" * 60)
    
    print("\nAvailable models:")
    for i, m in enumerate(fitting_models[:10], 1):
        rec = " ⭐" if m.recommended else ""
        print(f"  {i:2}. {m.name:30} ({m.size_gb:.1f} GB) {m.parameters}{rec}")
    
    if len(fitting_models) > 10:
        print(f"  ... and {len(fitting_models) - 10} more")
    
    print("\n  0. Enter custom HuggingFace repo/local path")
    print("-" * 60)
    
    choice = input("\nSelect model number (or press Enter for recommended): ").strip()
    
    if not choice:
        return best_model.repo_id
    elif choice == "0":
        return input("Enter model path or HF repo: ").strip()
    elif choice.isdigit() and 1 <= int(choice) <= len(fitting_models):
        return fitting_models[int(choice) - 1].repo_id
    else:
        print(f"Invalid choice, using recommended: {best_model.name}")
        return best_model.repo_id


def run_cli(args):
    """Run interactive CLI mode."""
    print_banner()
    
    # Hardware detection
    hw = detect_hardware()
    print_hardware_info(hw)
    
    # Initialize backend
    backend = LlamaCppBackend()
    
    if not backend.is_available():
        print("\n❌ llama-cpp-python not installed!")
        print("   Install with: pip install llama-cpp-python")
        print("   For GPU: pip install llama-cpp-python --extra-index-url ...")
        sys.exit(1)
    
    # Model selection
    if args.model:
        model_path = args.model
    else:
        model_path = select_model_interactive(hw)
    
    # Load model
    print(f"\n📥 Loading model: {model_path}")
    print("   (First run will download from HuggingFace)")
    
    try:
        backend.load_model(
            model_path,
            n_ctx=args.context_length,
            n_gpu_layers=args.gpu_layers,
        )
    except Exception as e:
        print(f"\n❌ Error loading model: {e}")
        sys.exit(1)
    
    # Chat loop
    print("\n" + "=" * 60)
    print("💬 CHAT MODE")
    print("=" * 60)
    print("Commands: 'quit' to exit, 'clear' to reset, 'stats' for info")
    print("=" * 60 + "\n")
    
    messages = []
    system_prompt = args.system or "You are a helpful AI assistant."
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == 'quit':
                print("\n👋 Goodbye!")
                break
            
            if user_input.lower() == 'clear':
                messages = []
                print("🗑️  Conversation cleared.\n")
                continue
            
            if user_input.lower() == 'stats':
                info = backend.model_info
                print(f"\n📊 Model: {info.name}")
                print(f"   Size: {info.size_gb:.1f} GB")
                print(f"   Context: {info.context_length}")
                print(f"   Messages: {len(messages)}\n")
                continue
            
            # Build messages
            chat_messages = [{"role": "system", "content": system_prompt}]
            chat_messages.extend(messages)
            chat_messages.append({"role": "user", "content": user_input})
            
            # Generate response
            print("Assistant: ", end="", flush=True)
            
            config = GenerationConfig(
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                stream=True,
            )
            
            full_response = ""
            final_stats = None
            
            for result in backend.chat(chat_messages, config):
                print(result.text, end="", flush=True)
                full_response += result.text
                final_stats = result
            
            print()
            
            if final_stats:
                print(f"   [{final_stats.tokens_generated} tokens, {final_stats.tokens_per_second:.1f} tok/s]\n")
            
            # Update history
            messages.append({"role": "user", "content": user_input})
            messages.append({"role": "assistant", "content": full_response})
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Use 'quit' to exit properly.")
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


def run_api(args):
    """Run OpenAI-compatible API server."""
    from localllm_studio.api import create_api_server
    
    print_banner()
    
    hw = detect_hardware()
    print_hardware_info(hw)
    
    backend = LlamaCppBackend()
    
    if not backend.is_available():
        print("\n❌ llama-cpp-python not installed!")
        sys.exit(1)
    
    # Pre-load model if specified
    if args.model:
        print(f"\n📥 Pre-loading model: {args.model}")
        backend.load_model(
            args.model,
            n_ctx=args.context_length,
            n_gpu_layers=args.gpu_layers,
        )
    
    # Start API server
    server = create_api_server(backend)
    server.run(host=args.host, port=args.port)


def run_web(args):
    """Run web UI."""
    from localllm_studio.ui import run_web_ui
    from localllm_studio.backends import LlamaCppBackend
    
    print_banner()
    
    hw = detect_hardware()
    print_hardware_info(hw)
    
    backend = LlamaCppBackend()
    
    if not backend.is_available():
        print("\n❌ llama-cpp-python not installed!")
        sys.exit(1)
    
    # Pre-load model if specified
    if args.model:
        print(f"\n📥 Pre-loading model: {args.model}")
        backend.load_model(
            args.model,
            n_ctx=args.context_length,
            n_gpu_layers=args.gpu_layers,
        )
    
    # Run professional Web UI
    run_web_ui(backend, port=7860)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description=f"{__app_name__} v{__version__} - Cross-Platform Local LLM Application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m localllm_studio                              # Interactive CLI
  python -m localllm_studio --model TheBloke/Llama-2-7B-GGUF  # Load specific model
  python -m localllm_studio --api --port 8000            # OpenAI-compatible API
  python -m localllm_studio --web                        # Web interface
        """
    )
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--api', action='store_true', help='Run OpenAI-compatible API server')
    mode_group.add_argument('--web', '-w', action='store_true', help='Run Web UI')
    
    # Model options
    parser.add_argument('--model', '-m', type=str, help='Model path or HuggingFace repo')
    parser.add_argument('--context-length', '-c', type=int, default=4096, help='Context length (default: 4096)')
    parser.add_argument('--gpu-layers', '-g', type=int, default=-1, help='GPU layers (-1=all, 0=CPU)')
    
    # Generation options
    parser.add_argument('--max-tokens', type=int, default=2048, help='Max tokens to generate')
    parser.add_argument('--temperature', '-t', type=float, default=0.7, help='Temperature (0.0-2.0)')
    parser.add_argument('--system', '-s', type=str, help='System prompt')
    
    # Server options
    parser.add_argument('--host', type=str, default='0.0.0.0', help='API host (default: 0.0.0.0)')
    parser.add_argument('--port', '-p', type=int, default=8000, help='API port (default: 8000)')
    
    # Other
    parser.add_argument('--version', '-v', action='version', version=f'{__app_name__} {__version__}')
    
    args = parser.parse_args()
    
    if args.api:
        run_api(args)
    elif args.web:
        run_web(args)
    else:
        run_cli(args)


if __name__ == "__main__":
    main()
