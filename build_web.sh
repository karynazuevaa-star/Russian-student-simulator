#!/bin/sh
set -eu

cd "$(dirname "$0")"

python3 -m venv .venv-web
. .venv-web/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-web.txt

STAGE_ROOT="$PWD/.web-stage"
STAGE_APP="$STAGE_ROOT/russian_student_simulator"
trap 'rm -rf "$STAGE_ROOT"' EXIT

rm -rf "$STAGE_ROOT"
mkdir -p "$STAGE_APP"
cp main.py "$STAGE_APP/main.py"
cp -R assets "$STAGE_APP/assets"
python optimize_web_assets.py "$STAGE_APP/assets"

python -m pygbag --build --width 900 --height 600 "$STAGE_APP/main.py"
python customize_web_index.py "$STAGE_APP/build/web/index.html"

rm -rf build/web
mkdir -p build
cp -R "$STAGE_APP/build/web" build/web

printf '\nWeb build complete: build/web/index.html\n'
