"""
PyInstaller hook for ONNX Runtime.

This hook ensures that all ONNX Runtime DLLs are properly collected,
including provider-specific DLLs and their nested dependencies.
It recursively gathers all DLL files from the onnxruntime package
to address the "DLL load failed while importing onnxruntime_pybind11_state"
error that commonly occurs with PyInstaller packaging.
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs

# Collect standard ONNX Runtime binaries
datas, binaries, hiddenimports = collect_all('onnxruntime')
extra_binaries = collect_dynamic_libs('onnxruntime')
binaries.extend(extra_binaries)

# Ensure all onnxruntime submodules are included
hiddenimports.extend([
    'onnxruntime.capi',
    'onnxruntime.capi._pybind_state',
    'onnxruntime.capi.onnxruntime_pybind11_state',
    'onnxruntime.providers',
    'onnxruntime.providers.cpu',
    'onnxruntime.providers.cuda',
    'onnxruntime.providers.dml',
    'onnxruntime.providers.openvino',
    'onnxruntime.providers.tensorrt',
    'onnxruntime.providers.rocm',
])

# Try to recursively collect ALL DLL files from onnxruntime package
try:
    import onnxruntime
    onnx_path = Path(onnxruntime.__file__).parent

    # Recursively add all DLLs and PYDs from the onnxruntime package
    for file_path in onnx_path.rglob("*"):
        if file_path.is_file() and file_path.suffix in ('.dll', '.pyd'):
            rel_path = file_path.relative_to(onnx_path)
            target_dir = (
                f"onnxruntime/{rel_path.parent}"
                if rel_path.parent != Path(".")
                else "onnxruntime"
            )
            binaries.append((str(file_path), target_dir))

            # Also add to datas for the file structure in _MEIPASS
            datas.append((str(file_path), target_dir))

except ImportError:
    # Fallback to searching common locations
    pass
except Exception as e:
    # Log the error but don't fail the build
    print(f"Warning: Could not collect ONNX Runtime DLLs recursively: {e}")

# Additional specific DLLs that are often missed
try:
    import onnxruntime as ort
    ort_path = Path(ort.__file__).parent

    # Look for specific provider DLLs that might be in subdirectories
    provider_dirs = ['providers', 'libs', 'capi']
    for provider_dir in provider_dirs:
        provider_path = ort_path / provider_dir
        if provider_path.exists():
            for dll in provider_path.rglob('*.dll'):
                rel_path = dll.relative_to(ort_path)
                target_dir = f"onnxruntime/{rel_path.parent}"
                binaries.append((str(dll), target_dir))

except Exception as e:
    print(f"Warning: Could not collect ONNX Runtime provider DLLs: {e}")
