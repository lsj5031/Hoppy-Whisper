# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Hoppy Whisper (Remote Transcription Mode - Windows).

This builds a minimal onedir layout excluding ONNX Runtime dependencies.
Use this when remote_transcription_enabled=true to reduce bundle size.
"""

import os
from pathlib import Path
import certifi

SCRIPT = 'src/app/__main__.py'

# Ensure required MSVC runtime DLLs are bundled (some systems lack these)
_msvc_binaries = []
try:
    _win = os.environ.get('SystemRoot') or os.environ.get('WINDIR')
    if _win:
        _sys32 = Path(_win) / 'System32'
        for _name in (
            'msvcp140_atomic_wait.dll',
            'msvcp140.dll',
            'vcruntime140.dll',
            'vcruntime140_1.dll',
            'ucrtbase.dll',
        ):
            _p = _sys32 / _name
            if _p.exists():
                # Place at _internal root for maximum compatibility
                _msvc_binaries.append((str(_p), '.'))
except Exception:
    pass

hidden = [
    # Core app/runtime deps
    'pystray', 'pynput', 'sounddevice', 'webrtcvad', 'pyperclip', 'numpy',
    'PIL', 'PIL.Image', 'PIL.ImageDraw',

    # requests stack for remote API calls
    'requests', 'urllib3', 'urllib3.util', 'urllib3.contrib', 'idna',
    'charset_normalizer', 'certifi',

    # Windows specifics
    'ctypes', 'ctypes.wintypes', 'winreg',
]

datas = [
    ('src/app/py.typed', 'app'),
    (certifi.where(), 'certifi'),
]

# Include tray ICO assets
try:
    ico_dir = Path('icos')
    if ico_dir.exists():
        for _ico in ico_dir.glob('*.ico'):
            datas.append((str(_ico), 'icos'))
    else:
        print('[HoppyWhisper_Remote.spec] Warning: icos directory not found; tray icons may fall back to transparent frames')
except Exception:
    pass

a = Analysis(
    [SCRIPT],
    pathex=[],
    binaries=_msvc_binaries,
    datas=datas,
    hiddenimports=hidden,
    hookspath=['.'],
    hooksconfig={},
    runtime_hooks=[],
    # Exclude ONNX and ML frameworks entirely
    excludes=[
        'onnxruntime', 'onnx', 'onnx_asr',
        'torch', 'tensorflow', 'transformers',
        'matplotlib', 'pandas', 'scipy', 'IPython', 'jupyter', 'notebook',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Hoppy Whisper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon='icos/BunnyPauseRounded.ico',
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='Hoppy Whisper',
)
