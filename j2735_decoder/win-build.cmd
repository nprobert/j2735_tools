set PYTHONPATH=..\classes;..\classes\j2735

python -m PyInstaller --clean --onefile --upx-dir d:\probestar\windows_tools\static\upx-4.0.2-win64 j2735_decoder.py
python -m PyInstaller --clean --onefile --upx-dir d:\probestar\windows_tools\static\upx-4.0.2-win64 j2735_decoder_gui.py
