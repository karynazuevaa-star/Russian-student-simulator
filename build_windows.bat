@echo off
setlocal
cd /d "%~dp0"

py -m venv .venv-build
call .venv-build\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt

python -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --windowed ^
    --onefile ^
    --name "Russian Student Simulator" ^
    --add-data "assets:assets" ^
    main.py

echo.
echo Build complete: dist\Russian Student Simulator.exe
endlocal
