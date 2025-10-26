"""PyInstaller runtime hook to help Windows locate ONNX Runtime native DLLs.

Adds the onefile extraction directory and common subfolders to both the DLL
search path and the PATH environment variable. Also proactively loads
onnxruntime core DLLs when present to avoid initialization failures.
"""

import ctypes
import logging
import os
import sys
from pathlib import Path

# Setup logging for debugging
LOGGER = logging.getLogger(__name__)

# Prefer the capi dir first (where the .pyd and DLLs normally live)
_CANDIDATES = (
    os.path.join("onnxruntime", "capi"),
    os.path.join("onnxruntime", "providers", "dml"),
    "onnxruntime",
    "onnxruntime.libs",
    os.path.join("onnxruntime", "libs"),
    "numpy.libs",
    ".",
)


def _add_dir(path: str) -> None:
    try:
        if os.path.isdir(path):
            os.add_dll_directory(path)  # type: ignore[attr-defined]
            # Also prepend to PATH for older loaders
            os.environ["PATH"] = path + os.pathsep + os.environ.get("PATH", "")
    except Exception:
        pass


if getattr(sys, "frozen", False):
    bases: list[Path] = []
    if hasattr(sys, "_MEIPASS"):
        try:
            bases.append(Path(sys._MEIPASS))  # type: ignore[attr-defined]
        except Exception:
            pass
    try:
        exe_dir = Path(sys.executable).parent
        bases.append(exe_dir)
        bases.append(exe_dir / "_internal")
    except Exception:
        pass

    # Preload VC++ redistributable DLLs to ensure they're available
    for base in bases:
        try:
            # Add root dir (where VC++ DLLs are) to DLL search and PATH
            os.add_dll_directory(str(base))
            os.environ["PATH"] = str(base) + os.pathsep + os.environ.get("PATH", "")

            # Core VC++ DLLs to preload
            vc_dlls = [
                'msvcp140.dll',
                'vcruntime140.dll',
                'vcruntime140_1.dll',
                'msvcp140_atomic_wait.dll',
                'ucrtbase.dll'
            ]

            for dll in vc_dlls:
                p = base / dll
                if p.exists():
                    try:
                        ctypes.WinDLL(str(p))  # Preload
                        LOGGER.debug(f"Preloaded VC++ DLL: {dll}")
                    except Exception as e:
                        if os.environ.get("HOPPY_WHISPER_ORT_DEBUG"):
                            LOGGER.warning(f"Failed to preload {dll}: {e}")
        except Exception as e:
            if os.environ.get("HOPPY_WHISPER_ORT_DEBUG"):
                LOGGER.warning(f"Failed to setup VC++ DLL preloading: {e}")

    for base in bases:
        _add_dir(str(base))
        for sub in _CANDIDATES:
            _add_dir(str(base / sub))

    # Best-effort: pre-load core ORT DLLs to ensure dependent imports succeed
    try:
        import ctypes

        debug = os.environ.get("HOPPY_WHISPER_ORT_DEBUG")
        debug_path: Path | None = None
        if debug:
            try:
                localappdata = os.environ.get(
                    "LOCALAPPDATA", str(bases[0] if bases else ".")
                )
                log_dir = Path(localappdata) / "Hoppy Whisper"
                log_dir.mkdir(parents=True, exist_ok=True)
                debug_path = log_dir / "ort_dll_debug.log"
                with debug_path.open("a", encoding="utf-8") as fh:
                    for b in bases:
                        fh.write(f"BASE={b}\n")
                    fh.write("DLL search candidates:\n")
                    for b in bases:
                        for sub in _CANDIDATES:
                            fh.write(f"  - {b / sub}\n")
            except Exception:
                debug_path = None

        for name in (
            "onnxruntime.dll",
            "onnxruntime_providers_shared.dll",
            "onnxruntime_providers_cpu.dll",
            "onnxruntime_providers_dml.dll",
            "onnxruntime_providers_directml.dll",
            "DirectML.dll",
        ):
            loaded = False
            for b in bases:
                for sub in _CANDIDATES:
                    p = b / sub / name
                    if p.exists():
                        try:
                            ctypes.WinDLL(str(p))
                            if debug_path:
                                try:
                                    with debug_path.open("a", encoding="utf-8") as fh:
                                        fh.write(f"Loaded: {p}\n")
                                except Exception:
                                    pass
                            loaded = True
                            break
                        except Exception as e:
                            if debug_path:
                                try:
                                    with debug_path.open("a", encoding="utf-8") as fh:
                                        fh.write(f"Failed load {p}: {e}\n")
                                except Exception:
                                    pass
                            continue
                if loaded:
                    break

        # Preload the pybind extension as a last resort to aid dependency resolution
        try:
            from glob import glob as _glob
            for b in bases:
                for sub in _CANDIDATES:
                    for _pyd in _glob(str(b / sub / "onnxruntime_pybind11_state*.pyd")):
                        try:
                            ctypes.WinDLL(_pyd)
                            if debug_path:
                                with debug_path.open("a", encoding="utf-8") as fh:
                                    fh.write(f"Preloaded pyd: {_pyd}\n")
                            break
                        except Exception as e:
                            if debug_path:
                                with debug_path.open("a", encoding="utf-8") as fh:
                                    fh.write(f"Failed preload pyd {_pyd}: {e}\n")
                            continue
        except Exception:
            pass

        # Optionally, attempt importing onnxruntime early (ignore failures)
        try:
            import importlib
            importlib.import_module("onnxruntime")
        except Exception:
            pass
    except Exception:
        # Silent: only best-effort to improve reliability
        pass
