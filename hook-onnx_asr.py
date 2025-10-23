from PyInstaller.utils.hooks import collect_data_files

# Collect all non-Python data files from the onnx_asr package
# (e.g., preprocessors/nemo128.onnx)
datas = collect_data_files('onnx_asr')
