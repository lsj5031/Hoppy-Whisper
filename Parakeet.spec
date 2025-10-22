# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Parakeet tray application.

This spec builds a single-file executable with:
- Embedded icon resources (generated dynamically)
- ONNXRuntime DirectML DLLs
- All Python dependencies
- Version metadata
"""

import sys
from pathlib import Path

block_cipher = None

# Determine if we're building with console or windowed mode
# Use windowed mode by default (no console window)
console_mode = False

a = Analysis(
    ['src/app/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Include the py.typed marker for type checking
        ('src/app/py.typed', 'app'),
    ],
    hiddenimports=[
        # Core dependencies
        'pystray',
        'pynput',
        'sounddevice',
        'webrtcvad',
        'pyperclip',
        'numpy',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        
        # ONNX Runtime and DirectML
        'onnxruntime',
        'onnxruntime.capi',
        'onnxruntime.capi.onnxruntime_pybind11_state',
        'onnx_asr',
        'huggingface_hub',
        
        # Standard library modules that might be missed
        'sqlite3',
        'json',
        'logging',
        'threading',
        'queue',
        'dataclasses',
        'functools',
        'pathlib',
        'urllib',
        'urllib.request',
        'hashlib',
        
        # Windows-specific
        'ctypes',
        'ctypes.wintypes',
        'winreg',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary packages to reduce size
        'matplotlib',
        'pandas',
        'scipy',
        'IPython',
        'jupyter',
        'notebook',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Parakeet',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=console_mode,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Icon will be generated dynamically by the app
    # icon='parakeet.ico',  # Uncomment if you add a static .ico file
    version='version_info.txt',  # Will be created separately if needed
)
