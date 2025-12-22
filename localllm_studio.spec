# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for LocalLLM Studio
Generates standalone executables for macOS, Windows, and Linux.
"""

import sys
import os
from PyInstaller.utils.hooks import collect_all, collect_submodules

# Determine platform
is_macos = sys.platform == 'darwin'
is_windows = sys.platform == 'win32'
is_linux = sys.platform.startswith('linux')

# Application metadata
APP_NAME = 'LocalLLM Studio'
APP_VERSION = '1.0.0'
APP_BUNDLE_ID = 'com.localllm.studio'

# Collect all dependencies
datas = []
binaries = []
hiddenimports = []

# Collect llama_cpp binaries and data
try:
    llama_datas, llama_binaries, llama_hiddenimports = collect_all('llama_cpp')
    datas.extend(llama_datas)
    binaries.extend(llama_binaries)
    hiddenimports.extend(llama_hiddenimports)
except Exception as e:
    print(f"Warning: Could not collect llama_cpp: {e}")

# Collect huggingface_hub
try:
    hf_datas, hf_binaries, hf_hiddenimports = collect_all('huggingface_hub')
    datas.extend(hf_datas)
    binaries.extend(hf_binaries)
    hiddenimports.extend(hf_hiddenimports)
except Exception as e:
    print(f"Warning: Could not collect huggingface_hub: {e}")

# Add common hidden imports
hiddenimports.extend([
    'flask',
    'werkzeug',
    'jinja2',
    'markupsafe',
    'itsdangerous',
    'click',
    'webview',
    'huggingface_hub',
    'requests',
    'urllib3',
    'certifi',
    'charset_normalizer',
    'idna',
    'tqdm',
    'filelock',
    'packaging',
    'pyyaml',
    'typing_extensions',
])

# Platform-specific webview backends
if is_macos:
    hiddenimports.extend(['webview.platforms.cocoa'])
elif is_windows:
    hiddenimports.extend(['webview.platforms.winforms', 'webview.platforms.edgechromium'])
elif is_linux:
    hiddenimports.extend(['webview.platforms.gtk'])

# Add our source files
datas.extend([
    ('ui', 'ui'),
    ('backends', 'backends'),
    ('models', 'models'),
    ('utils', 'utils'),
])

# Analysis
a = Analysis(
    ['desktop.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy.testing',
        'scipy',
        'pandas',
        'PIL',
        'tkinter',
        'PyQt5',
        'PyQt6',
    ],
    noarchive=False,
    optimize=1,
)

# Remove unnecessary files to reduce size
a.binaries = [x for x in a.binaries if not x[0].startswith('libQt')]
a.binaries = [x for x in a.binaries if 'test' not in x[0].lower()]

pyz = PYZ(a.pure, a.zipped_data)

# Executable
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='LocalLLM Studio' if (is_macos or is_windows) else 'localllm-studio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=True if is_macos else False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.icns' if is_macos else ('assets/icon.ico' if is_windows else None),
)

# macOS App Bundle
if is_macos:
    app = BUNDLE(
        exe,
        name='LocalLLM Studio.app',
        icon='assets/icon.icns' if os.path.exists('assets/icon.icns') else None,
        bundle_identifier=APP_BUNDLE_ID,
        version=APP_VERSION,
        info_plist={
            'CFBundleName': APP_NAME,
            'CFBundleDisplayName': APP_NAME,
            'CFBundleVersion': APP_VERSION,
            'CFBundleShortVersionString': APP_VERSION,
            'CFBundleIdentifier': APP_BUNDLE_ID,
            'NSHighResolutionCapable': True,
            'LSUIElement': False,  # Show in dock
            'NSRequiresAquaSystemAppearance': False,  # Support dark mode
        },
    )
