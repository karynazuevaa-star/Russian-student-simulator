# Building the game

The game must be built separately on each target operating system.

## macOS

Run from Terminal:

```sh
./build_macos.sh
```

The distributable application will be:

```text
dist/Russian Student Simulator.app
```

Compress the `.app` into a ZIP before uploading it.

Unsigned applications may be blocked by macOS Gatekeeper. For public
distribution, sign and notarize the application with an Apple Developer
account. For private testing, a player can right-click the app and choose
Open.

## Windows

Copy the project to a Windows computer with Python installed, then run:

```bat
build_windows.bat
```

The distributable file will be:

```text
dist\Russian Student Simulator.exe
```

PyInstaller does not produce a Windows executable from macOS, so this build
must run on Windows or in a Windows virtual machine.

## Publishing

For a simple public download, upload the ZIP or EXE to an itch.io project.
Google Drive or GitHub Releases also work for private testing.

Do not upload the `build`, `.venv-build`, or `__pycache__` directories.

## Browser and Vercel

Build the browser version locally:

```sh
./build_web.sh
```

The static website will be generated in:

```text
build/web
```

Test it through a local HTTP server rather than opening `index.html` directly:

```sh
python3 -m http.server 8000 --directory build/web
```

Then open `http://localhost:8000`.

For Vercel, push the project to a Git repository and import that repository.
The included `vercel.json` runs the pygbag build and publishes `build/web`.
The build optimizes copies of the PNG assets for the browser; original assets
are not modified. Do not commit `build/web` or the desktop ZIP.
