# LocalLLM Studio

🚀 **Run AI models privately on your device. No internet required once downloaded.**

![LocalLLM Studio](https://img.shields.io/badge/version-1.0.0-blue)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

- 🔒 **100% Private** - Your data never leaves your computer
- ⚡ **Fast** - Optimized for Apple Silicon, NVIDIA GPUs, and CPU
- 📦 **Easy Install** - Just download and run, no setup required
- 🌐 **Offline** - Works without internet (after first model download)
- 💬 **Chat Interface** - Beautiful, modern UI for conversations

## Quick Start

### Download Pre-built Installers

| Platform | Download | Requirements |
|----------|----------|--------------|
| **macOS** | [LocalLLM-Studio.dmg](#) | macOS 11+ (Apple Silicon or Intel) |
| **Windows** | [LocalLLM-Studio-Setup.exe](#) | Windows 10/11 (64-bit) |
| **Linux** | [LocalLLM-Studio.AppImage](#) | Any modern Linux (64-bit) |

### Installation

#### macOS
1. Download the `.dmg` file
2. Double-click to open
3. Drag **LocalLLM Studio** to **Applications**
4. Launch from Applications

> **First launch**: Right-click → Open (to bypass Gatekeeper)

#### Windows
1. Download the `.exe` installer
2. Double-click to run
3. Follow the installation wizard
4. Launch from Start Menu

#### Linux
1. Download the `.AppImage` file
2. Make it executable: `chmod +x LocalLLM-Studio*.AppImage`
3. Double-click or run: `./LocalLLM-Studio*.AppImage`

---

## Building from Source

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

### Build Commands

```bash
# Clone the repository
git clone https://github.com/yourusername/localllm-studio.git
cd localllm-studio

# Build for your platform
./scripts/build_macos.sh    # macOS
./scripts/build_windows.bat  # Windows
./scripts/build_linux.sh     # Linux
```

### Development Mode

```bash
# Install dependencies
pip install -r requirements.txt

# Run the desktop app
python desktop.py

# Or run as web server (for development)
python -m localllm_studio --web
```

---

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **RAM** | 8 GB | 16 GB+ |
| **Storage** | 10 GB free | 50 GB+ (for multiple models) |
| **GPU** | None (CPU works) | Apple M1+ / NVIDIA with 6GB+ VRAM |

### Supported Models

The app automatically downloads models from HuggingFace. Recommended models:

| Model | Size | RAM Needed | Best For |
|-------|------|------------|----------|
| Qwen2.5 0.5B | 0.4 GB | 2 GB | Testing, low-end devices |
| Qwen2.5 1.5B | 1.1 GB | 4 GB | Everyday use |
| Qwen2.5 3B | 2.0 GB | 6 GB | Better quality |
| Mistral 7B | 4.4 GB | 10 GB | High quality |
| Llama 3.2 3B | 2.0 GB | 6 GB | General purpose |

---

## Architecture

```
localllm_studio/
├── desktop.py          # Desktop app entry point
├── localllm_studio.spec # PyInstaller configuration
├── requirements.txt
├── scripts/
│   ├── build_macos.sh   # macOS build script
│   ├── build_windows.bat # Windows build script
│   ├── build_linux.sh   # Linux AppImage script
│   └── create_dmg.sh    # macOS DMG creator
├── ui/
│   └── web.py          # Flask web interface
├── backends/
│   └── llamacpp.py     # LLM inference backend
├── models/
│   └── library.py      # Model definitions
└── utils/
    └── hardware.py     # Hardware detection
```

---

## Troubleshooting

### macOS: "App is damaged" error
```bash
xattr -cr /Applications/LocalLLM\ Studio.app
```

### Windows: "Windows protected your PC"
Click "More info" → "Run anyway"

### Linux: App won't start
Make sure you have WebKitGTK installed:
```bash
# Ubuntu/Debian
sudo apt install libwebkit2gtk-4.0-37

# Fedora
sudo dnf install webkit2gtk3
```

### Model download stuck
- Check your internet connection
- Try a smaller model first
- Models are cached in `~/.cache/huggingface/`

---

## License

MIT License - see [LICENSE](LICENSE)

---

## Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

---

Built with ❤️ for privacy-conscious AI users
