# Set up

Set up connects your coding agent to your running app. Once per project.

## 1. Install the dev extra

`[dev]` carries the dev bridge's MCP server.

=== "uv"

    ```bash
    uv add nuiitivet
    uv add --dev 'nuiitivet[dev]'
    ```

=== "pip"

    ```bash
    pip install 'nuiitivet[dev]'
    ```

## 2. Install the skills

[The skills](skills.md) says what each of the three does for you. Install all
three, by whichever route fits your agent:

=== "From the package"

    ```bash
    python -m nuiitivet.skills install
    ```

    That installs them into Claude's directory, `.claude/skills/`. The other
    destinations:

    ```bash
    # personal (available in every project) — for Claude, ~/.claude/skills/
    python -m nuiitivet.skills install --user

    # another agent's skills directory — e.g. GitHub Copilot
    python -m nuiitivet.skills install --dest .github/skills
    ```

    Re-run it after upgrading nuiitivet.

=== "Claude Code plugin"

    ```text
    /plugin marketplace add yuksblog/nuiitivet
    /plugin install nuiitivet
    ```

    The plugin installs the three skills and registers the MCP server.

=== "By hand"

    The skills live in the Nuiitivet repository under
    [`skills/`](https://github.com/yuksblog/nuiitivet/tree/main/skills). From
    a checkout, copy the three directories into your agent's skills
    directory; the example is Claude's:

    ```bash
    cp -r path/to/nuiitivet/skills/nuiitivet-* .claude/skills/
    ```

    Without a checkout, one at a time:

    ```bash
    npx degit yuksblog/nuiitivet/skills/nuiitivet-app .claude/skills/nuiitivet-app
    ```

## 3. Register the MCP server

Add `python -m nuiitivet.dev mcp` to your MCP host's server list. For Claude
Code that is `.mcp.json` at the project root:

=== "macOS / Linux"

    ```json
    {
      "mcpServers": {
        "nuiitivet-dev": {
          "command": ".venv/bin/python",
          "args": ["-m", "nuiitivet.dev", "mcp"]
        }
      }
    }
    ```

=== "Windows"

    ```json
    {
      "mcpServers": {
        "nuiitivet-dev": {
          "command": ".venv\\\\Scripts\\\\python.exe",
          "args": ["-m", "nuiitivet.dev", "mcp"]
        }
      }
    }
    ```

=== "Claude Code plugin"

    Nothing to do: the plugin did it in step 2.

The `command` is relative to where the host starts the server, the project
root for Claude Code. If your host starts elsewhere, give the venv's python
as an absolute path.

## 4. Pass a root factory to the window

```python
import nuiitivet.material as nv

class Counter(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.count = nv.Observable(0)

    def build(self) -> nv.Widget:
        return nv.Column(
            padding=16,
            children=[
                nv.Text(self.count.map(lambda n: f"Count: {n}")),
                nv.Button("increment", on_click=lambda: self._inc()),
            ],
        )

    def _inc(self) -> None:
        self.count.value += 1

def build_root() -> nv.Widget:
    return Counter()

def main() -> None:
    nv.App(nv.Window(content=build_root)).run()

if __name__ == "__main__":
    main()
```

`Window` takes the factory itself, `build_root`, not a call to it. With
`Window(content=build_root())` edits stop applying to that window. The dev
runner warns about it.

## 5. Launch under the dev runner

=== "Terminal"

    ```bash
    python -m nuiitivet.dev run path/to/app.py
    ```

    A package module launches by name:

    ```bash
    python -m nuiitivet.dev run --module yourpkg.app
    ```

    Arguments for your app go after a `--` separator. Everything past it
    becomes the app's `sys.argv`:

    ```bash
    python -m nuiitivet.dev run app.py -- --png out.png
    ```

=== "VS Code"

    Add this to `.vscode/launch.json` and press **F5**:

    ```json
    {
      "name": "nuiitivet: hot reload",
      "type": "debugpy",
      "request": "launch",
      "module": "nuiitivet.dev",
      "args": ["run", "${workspaceFolder}/app.py"],
      "console": "integratedTerminal"
    }
    ```

    Arguments for your app go into `args`, after a `"--"` entry.

`python app.py` still runs the app as before.

## 6. Confirm the connection

Run `python -m nuiitivet.dev status`, or ask the agent to call `status`. It
prints the running app's window title. Check it is your app. A "no running
app" error means the app is not up under the dev runner.

## Next Steps

- [Hot Reload](hot_reload.md) — what a save does to the running window, and
  what it does not restore.
- [With a coding agent](index.md) — the section overview.
