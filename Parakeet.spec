# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Parakeet (Windows).

This builds an onedir layout for easier inspection/debugging of bundled DLLs.
Set PARAKEET_INCLUDE_DML=1 to include DirectML provider binaries (when using
onnxruntime-directml). By default, we bundle CPU-only ORT binaries.
"""

import os
from pathlib import Path
import certifi
from PyInstaller.utils.hooks import collect_dynamic_libs

SCRIPT = 'src/app/__main__.py'
INCLUDE_DML = bool(os.environ.get('PARAKEET_INCLUDE_DML'))

# Collect ORT dynamic libraries and ensure capi/provider bits are present.
_ort_binaries = []
try:
    _ort_binaries = collect_dynamic_libs('onnxruntime')
    try:
        import onnxruntime as _ort  # type: ignore
        _pkg_dir = Path(_ort.__file__).parent
        _capi_dir = _pkg_dir / 'capi'

        # Recursively collect all DLL files from onnxruntime package
        for file_path in _pkg_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in ('.dll', '.pyd'):
                # Determine relative path and target directory (keeping structure)
                rel_path = file_path.relative_to(_pkg_dir)
                target_dir = f"onnxruntime/{rel_path.parent}" if rel_path.parent != Path(".") else "onnxruntime"
                _ort_binaries.append((str(file_path), target_dir))

        core_names = [
            'onnxruntime.dll',
            'onnxruntime_providers_shared.dll',
            'onnxruntime_providers_cpu.dll',
        ]
        if INCLUDE_DML:
            core_names += [
                'onnxruntime_providers_dml.dll',
                'onnxruntime_providers_directml.dll',
                'DirectML.dll',
            ]

        # Ensure these core DLLs are explicitly included in capi directory
        for _name in core_names:
            _p = _capi_dir / _name
            if _p.exists():
                _ort_binaries.append((str(_p), str(Path('onnxruntime') / 'capi')))

        # Ensure pybind state lives under onnxruntime/capi
        try:
            from glob import glob as _glob
            for _pyd in _glob(str(_capi_dir / 'onnxruntime_pybind11_state*.pyd')):
                _ort_binaries.append((_pyd, str(Path('onnxruntime') / 'capi')))
        except Exception:
            pass

        # Some wheels may ship DirectML.dll under onnxruntime/libs
        if INCLUDE_DML:
            try:
                _libs_dir = _pkg_dir / 'libs'
                _p = _libs_dir / 'DirectML.dll'
                if _p.exists():
                    _ort_binaries.append((str(_p), str(Path('onnxruntime') / 'capi')))
            except Exception:
                pass

        # Provider-specific DLLs under providers/dml
        if INCLUDE_DML:
            try:
                _dml_dir = _pkg_dir / 'providers' / 'dml'
                if _dml_dir.exists():
                    for _dll in _dml_dir.glob('*.dll'):
                        _ort_binaries.append((str(_dll), str(Path('onnxruntime') / 'capi')))
            except Exception:
                pass
    except Exception:
        pass
except Exception:
    _ort_binaries = []

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
                
    # Also try to collect from vcpkg/conan installations if available
    _vcpkg_paths = [
        Path('C:/vcpkg/installed/x64-windows/bin'),
        Path('C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Redist/MSVC'),
        Path('C:/Program Files (x86)/Microsoft Visual Studio/2019/Community/VC/Redist/MSVC'),
    ]
    
    for _vcpkg_base in _vcpkg_paths:
        if not _vcpkg_base.exists():
            continue
            
        # Look for the latest version subdirectory in MSVC
        for _ver_dir in _vcpkg_base.glob('14.*'):
            if not _ver_dir.is_dir():
                continue
            for _arch_dir in ['x64', 'x86', 'onecore']:
                _bin_dir = _ver_dir / _arch_dir
                if not _bin_dir.exists():
                    continue
                for _name in ('msvcp140_atomic_wait.dll', 'msvcp140.dll', 'vcruntime140.dll', 'vcruntime140_1.dll', 'ucrtbase.dll'):
                    _p = _bin_dir / _name
                    if _p.exists():
                        _msvc_binaries.append((str(_p), '.'))
except Exception:
    pass

hidden = [
    # Core app/runtime deps
    'pystray', 'pynput', 'sounddevice', 'webrtcvad', 'pyperclip', 'numpy',
    'PIL', 'PIL.Image', 'PIL.ImageDraw',

    # ONNX Runtime & model stack
    'onnxruntime', 'onnxruntime.capi', 'onnxruntime.capi._pybind_state',
    'onnxruntime.capi.onnxruntime_pybind11_state',
    'onnx_asr', 'huggingface_hub',

    # requests stack used by huggingface_hub
    'requests', 'urllib3', 'urllib3.util', 'urllib3.contrib', 'idna',
    'charset_normalizer', 'certifi',

    # Windows specifics sometimes missed
    'ctypes', 'ctypes.wintypes', 'winreg',
]
if INCLUDE_DML:
    hidden += ['onnxruntime.providers', 'onnxruntime.providers.dml']

datas = [
    ('src/app/py.typed', 'app'),
    (certifi.where(), 'certifi'),
]

# Include onnx_asr preprocessors (e.g., nemo128.onnx) so the frozen app can read them
try:
    import onnx_asr as _asr  # type: ignore
    _asr_pkg_dir = Path(_asr.__file__).parent
    _pp_dir = _asr_pkg_dir / 'preprocessors'
    if _pp_dir.exists():
        for _f in _pp_dir.rglob('*'):
            if _f.is_file():
                _rel = _f.relative_to(_asr_pkg_dir)
                # Preserve package-relative directory structure under _internal
                datas.append((str(_f), str(_rel.parent)))
except Exception:
    # If onnx_asr isn't importable at spec-eval time, skip quietly
    pass

a = Analysis(
    [SCRIPT],
    pathex=[],
    binaries=_ort_binaries + _msvc_binaries,
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['pyi_rth_onnx_dlls.py'],
    excludes=['matplotlib', 'pandas', 'scipy', 'IPython', 'jupyter', 'notebook'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Parakeet',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
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
    upx_exclude=['onnxruntime_pybind11_state.pyd', 'onnxruntime.dll', 'onnxruntime_providers_shared.dll'],
    name='Parakeet',
)
