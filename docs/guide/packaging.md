# Packaging

This guide explains how to package your Nuiitivet application into a standalone executable.

## Choosing a Tool

There are two popular tools for packaging Python applications: **PyInstaller** and **Nuitka**.

| Feature | PyInstaller | Nuitka |
| :--- | :--- | :--- |
| **Build Speed** | 🚀 Fast | 🐢 Slow (Compiles to C) |
| **Startup Speed** | 😐 Normal | 🚀 Fast |
| **Setup** | Easy | Moderate |
| **Obfuscation** | Low | High |

- **Use PyInstaller** for quick prototyping, testing, or internal tools.
- **Use Nuitka** for public releases where startup performance and code protection matter.

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

Run the following command to build a single executable file:

```bash
pyinstaller main.py --name "MyApp" --onefile --noconsole --clean

# Or with uv
uv run pyinstaller main.py --name "MyApp" --onefile --noconsole --clean
```

### Options

| Option | Required? | Description |
| :--- | :--- | :--- |
| `--onefile` | No | Bundle everything into a single executable. <br> **Pros:** Easy distribution. **Cons:** Slower startup (unpacks to temp dir). |
| `--onedir` | No | (Default) Create a directory with the executable and dependencies. <br> **Pros:** Faster startup. **Cons:** Must distribute the whole folder. |
| `--noconsole` | No | Hide the terminal window. Recommended for GUI apps. |
| `--clean` | No | Clean PyInstaller cache before building. |
| `--name "Name"` | No | Specify the name of the executable. |

### 3. Result

The executable will be created in the `dist/` directory.

## Using Nuitka

Nuitka compiles your Python code to C, resulting in faster execution and harder-to-reverse-engineer binaries.

### 1. Install Nuitka

```bash
pip install nuitka

# Or with uv
uv add --dev nuitka
```

### 2. Build

Run Nuitka with the following recommended flags. Since Nuiitivet relies on data files (like icons), we ensure package data is included.

```bash
python -m nuitka main.py \
    --standalone \
    --onefile \
    --include-package=nuiitivet \
    --include-package-data=nuiitivet \
    --output-dir=dist \
    --output-filename=MyApp \
    --enable-plugin=anti-bloat

# Or with uv
# uv run python -m nuitka ...
```

### Options

| Option | Required? | Description |
| :--- | :--- | :--- |
| `--standalone` | **YES** | Make the executable standalone (includes Python runtime). |
| `--include-package=nuiitivet` | **YES** | Must be set to `nuiitivet`. Forces inclusion of the package to handle lazy imports. |
| `--include-package-data=nuiitivet`| **YES** | Must be set to `nuiitivet`. Bundles assets like fonts and icons. |
| `--onefile` | No | Create a single executable file. |
| `--output-dir` | No | Directory to put the result in (e.g., `dist`). |
| `--enable-plugin` | No | `anti-bloat` is recommended to reduce file size. |

### 3. Result

The executable will be created in the `dist/` directory.
