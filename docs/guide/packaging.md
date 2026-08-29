# Packaging

This guide explains how to package your Nuiitivet application into a standalone executable.

## Choosing a Tool

There are two popular tools for packaging Python applications: **PyInstaller** and **Nuitka**.

| Feature | PyInstaller | Nuitka |
| :--- | :--- | :--- |
| **Build Speed** | 🚀 Fast | 🐢 Slow (compiles to C) |
| **Startup / Runtime Speed** | 😐 Normal | 🚀 Fast |
| **C Compiler** | Not required | Required |

The rule of thumb follows your development lifecycle:

- **During development, use PyInstaller.** Builds are fast, so you can iterate quickly.
- **For production releases, use Nuitka.** Startup and runtime are faster, which is what your users experience.

## Using PyInstaller

Nuiitivet includes built-in hooks for PyInstaller, making the setup very simple.

### 1. Install PyInstaller

Add PyInstaller to your development dependencies:

```bash
pip install pyinstaller

# Or with uv
uv add --dev pyinstaller
```

### 2. Build

Run the following command. We recommend `--onedir` for faster startup:

```bash
# Works on every OS: --noconsole hides the console on Windows,
# builds a .app bundle on macOS, and is ignored on Linux.
pyinstaller main.py --name "MyApp" --onedir --noconsole --clean

# Or with uv
uv run pyinstaller main.py --name "MyApp" --onedir --noconsole --clean
```

### Common Options

| Option | Required? | Description |
| :--- | :--- | :--- |
| `--onedir` | No | (Recommended, default) Create a directory with the executable and dependencies. <br> **Pros:** Faster startup. **Cons:** Must distribute the whole folder. |
| `--onefile` | No | Bundle everything into a single executable. <br> **Pros:** Easy distribution. **Cons:** Slower startup (unpacks to a temp dir). |
| `--clean` | No | Clean PyInstaller cache before building. |
| `--name "Name"` | No | Specify the name of the executable. |
| `--icon path/to/icon` | No | Set the app icon. Cross-platform flag; only the file format differs (`.ico` on Windows, `.icns` on macOS). |

### Platform-Specific Options

| Option | Required? | Description |
| :--- | :--- | :--- |
| `--windowed` (alias `--noconsole`) | No | Recommended for GUI apps; combine freely with `--onedir` or `--onefile`. **Windows:** hide the console window. **macOS:** hide the console *and* build a `.app` bundle. **Linux:** ignored, so you can omit it. |
| `--osx-bundle-identifier com.example.myapp` | No | **macOS only.** Set the bundle identifier of the `.app`. Needed for OS features keyed to app identity — see [macOS App Identity](#macos-app-identity). |

### 3. Result

The executable will be created in the `dist/` directory.

## Using Nuitka

Nuitka compiles your Python code to C, resulting in faster startup and execution.

### 1. Install Nuitka

```bash
pip install nuitka

# Or with uv
uv add --dev nuitka
```

Nuitka compiles to C, so it needs a **C compiler**. The required compiler differs per OS (MSVC/MinGW64 on Windows, Clang via Xcode on macOS, GCC on Linux). See Nuitka's [Requirements](https://nuitka.net/user-documentation/user-manual.html#requirements) for the details.

### 2. Build

Run Nuitka with the following recommended flags. `--standalone` (without `--onefile`) produces a directory, which starts faster. Since Nuiitivet relies on data files (like icons), we ensure package data is included.

```bash
# This example targets Windows. On macOS, drop --windows-console-mode=disable
# and add --macos-create-app-bundle (see Platform-Specific Options).
python -m nuitka main.py \
    --standalone \
    --include-package=nuiitivet \
    --include-package-data=nuiitivet \
    --windows-console-mode=disable \
    --output-dir=dist \
    --output-filename=MyApp \
    --enable-plugin=anti-bloat

# Or with uv
# uv run python -m nuitka ...
```

### Common Options

| Option | Required? | Description |
| :--- | :--- | :--- |
| `--standalone` | **YES** | Make the executable standalone (includes Python runtime). Produces a directory (recommended for faster startup). |
| `--include-package=nuiitivet` | **YES** | Must be set to `nuiitivet`. Forces inclusion of the package to handle lazy imports. |
| `--include-package-data=nuiitivet` | **YES** | Must be set to `nuiitivet`. Bundles assets like fonts and icons. |
| `--onefile` | No | Bundle into a single executable. Easier to distribute, but slower to start (unpacks to a temp dir). |
| `--output-dir` | No | Directory to put the result in (e.g., `dist`). |
| `--enable-plugin` | No | `anti-bloat` is recommended to reduce file size. |

### Platform-Specific Options

| Option | Required? | Description |
| :--- | :--- | :--- |
| `--windows-console-mode=disable` | No | **Windows only.** Hide the console window for GUI apps. Ignored on macOS/Linux — no need to write it there. |
| `--macos-create-app-bundle` | No | **macOS only.** Build a `.app` bundle. A `.app` is a directory, so pair it with the recommended `--standalone` build (not with `--onefile`). |
| `--macos-app-icon=icon` / `--windows-icon-from-ico=icon` | No | Set the app icon on macOS / Windows. Nuitka has no Linux icon flag — on Linux, the icon is set via a `.desktop` file, not embedded in the binary. |
| `--macos-signed-app-name=com.example.myapp` | No | **macOS only.** Set the bundle identifier the `.app` is signed under — see [macOS App Identity](#macos-app-identity). |

### 3. Result

The executable will be created in the `dist/` directory.

## macOS App Identity

Some OS features only work for an app the system can identify — concretely,
[desktop notifications](window/notifications.md) (`nv.Desktop.notify`) are only
delivered natively, under your app's own name and icon, when the process runs
from a `.app` bundle that has a **bundle identifier** and a code signature.
A build without them still runs; notifications just stay on the fallback path
with borrowed attribution.

To give your app an identity:

1. **Set a bundle identifier** — a reverse-DNS string that is yours, e.g.
   `com.example.myapp`. Pass `--osx-bundle-identifier` (PyInstaller) or
   `--macos-signed-app-name` (Nuitka), as in the tables above. Keep it stable
   across releases: the OS keys the user's notification permission (and their
   per-app settings row in System Settings → Notifications) to this string.
2. **Sign the bundle.** PyInstaller applies an *ad-hoc* signature by default,
   which is enough for the app to work on the machine that built it. To
   distribute to other machines you need a Developer ID certificate and
   notarization either way — that general macOS distribution setup is beyond
   this guide.

Windows and Linux need nothing here: no notification feature in nuiitivet
requires a registered app identity on those platforms.
