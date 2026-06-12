#!/bin/sh
set -eu

cd "$(dirname "$0")"

python3 -m venv .venv-build
. .venv-build/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt

python -m PyInstaller \
    --noconfirm \
    --clean \
    --windowed \
    --onedir \
    --name "Russian Student Simulator" \
    --osx-bundle-identifier "com.russianstudentsimulator.game" \
    --add-data "assets:assets" \
    main.py

printf '\nBuild complete: dist/Russian Student Simulator.app\n'
