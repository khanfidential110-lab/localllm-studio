# LocalLLM Studio

<p align="center">
  <img src="assets/icon.ico" alt="LocalLLM Studio" width="128">
</p>

<p align="center">
  <strong>🚀 Run AI models privately on your device. No internet required.</strong>
</p>

<p align="center">
  <a href="https://github.com/khanfidential110-lab/localllm-studio/releases/latest">
    <img src="https://img.shields.io/github/v/release/khanfidential110-lab/localllm-studio?style=flat-square&color=blue" alt="Latest Release">
  </a>
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey?style=flat-square" alt="Platform">
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License">
  </a>
  <a href="https://github.com/khanfidential110-lab/localllm-studio/actions">
    <img src="https://img.shields.io/github/actions/workflow/status/khanfidential110-lab/localllm-studio/build.yml?style=flat-square" alt="Build Status">
  </a>
</p>

---

## ✨ Features

- 🔒 **100% Private** – Your data never leaves your computer
- ⚡ **Fast** – Optimized for Apple Silicon (Metal), NVIDIA GPUs, and CPU
- 📦 **Easy Install** – Download and run, no setup required
- 🌐 **Offline** – Works without internet after first model download
- 💬 **Beautiful UI** – Modern, Google-inspired chat interface
- 🛠️ **Model Management** – Load, unload, and switch models easily

---

## 📥 Download

| Platform | Download | Requirements |
|:--------:|:--------:|:-------------|
| <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/windows8/windows8-original.svg" width="24"> **Windows** | [**Download .exe**](https://github.com/khanfidential110-lab/localllm-studio/releases/latest/download/LocalLLM-Studio-Setup.exe) | Windows 10/11 (64-bit) |
| <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/apple/apple-original.svg" width="24"> **macOS** | [**Download .dmg**](https://github.com/khanfidential110-lab/localllm-studio/releases/latest/download/LocalLLM-Studio-macOS.dmg) | macOS 12+ (Intel & Apple Silicon) |
| <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/linux/linux-original.svg" width="24"> **Linux** | [**Download AppImage**](https://github.com/khanfidential110-lab/localllm-studio/releases/latest/download/LocalLLM-Studio-Linux.AppImage) | Ubuntu, Fedora, Debian (64-bit) |

---

## 🚀 Quick Start

### macOS
1. Download the `.dmg` file
2. Open and drag **LocalLLM Studio** to **Applications**
3. Right-click → Open (first launch only)

### Windows
1. Download the `.exe` installer
2. Run and follow the installation wizard
3. Launch from Start Menu

### Linux
```bash
chmod +x LocalLLM-Studio-Linux.AppImage
./LocalLLM-Studio-Linux.AppImage
```

---

## 💻 System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **RAM** | 8 GB | 16 GB+ |
| **Storage** | 10 GB free | 50 GB+ |
| **GPU** | None (CPU works) | Apple M1+ / NVIDIA 6GB+ VRAM |

---

## 🤖 Supported Models

Models are downloaded automatically from HuggingFace:

| Model | Size | RAM Needed | Best For |
|-------|------|------------|----------|
| Qwen2.5 0.5B | 0.4 GB | 2 GB | Testing, low-end devices |
| Qwen2.5 1.5B | 1.1 GB | 4 GB | Everyday use |
| Qwen2.5 3B | 2.0 GB | 6 GB | Better quality |
| Llama 3.2 3B | 2.0 GB | 6 GB | General purpose |
| Mistral 7B | 4.4 GB | 10 GB | High quality |

---

## 🔧 Building from Source

```bash
# Clone
git clone https://github.com/khanfidential110-lab/localllm-studio.git
cd localllm-studio

# Install dependencies
pip install -r requirements.txt
pip install llama-cpp-python  # Add GPU flags as needed

# Run
python desktop.py
```

---

## 🐛 Troubleshooting

<details>
<summary><strong>macOS: "App is damaged" error</strong></summary>

```bash
xattr -cr /Applications/LocalLLM\ Studio.app
```
</details>

<details>
<summary><strong>Windows: "Windows protected your PC"</strong></summary>

Click "More info" → "Run anyway"
</details>

<details>
<summary><strong>Linux: App won't start</strong></summary>

Install WebKitGTK:
```bash
# Ubuntu/Debian
sudo apt install libwebkit2gtk-4.1-0

# Fedora
sudo dnf install webkit2gtk4.1
```
</details>

---

## 📄 License

MIT License – see [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

Contributions welcome! Feel free to open issues or submit pull requests.

---

<p align="center">
  Built with ❤️ for privacy-conscious AI users
</p>
