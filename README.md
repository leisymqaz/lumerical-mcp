# Lumerical Multi-Product MCP

Control Ansys Lumerical from an MCP-capable AI client such as Codex.

This project exposes a small MCP server around Lumerical's bundled Python API, `lumapi.py`. It supports:

- FDTD Solutions through `lumapi.FDTD`
- MODE Solutions through `lumapi.MODE`
- INTERCONNECT through `lumapi.INTERCONNECT`
- DEVICE through `lumapi.DEVICE`

The original `fdtd_*` tools are still available for compatibility. New work should use the generic `lumerical_*` tools with `product=fdtd|mode|interconnect|device`.

## Why

The goal is to make photonic simulation workflows easier to drive from an AI coding agent:

- Detect local Lumerical paths and product availability.
- Open visible or hidden product sessions.
- Execute Lumerical script snippets through MCP tools.
- Keep sessions alive across multiple tool calls.
- Load and save project files: `.fsp`, `.lms`, `.icp`, `.ldev`.
- Build simple optical, circuit, and device structures from natural-language instructions.

## Tools

Generic tools:

- `lumerical_detect_tool`: detect Lumerical executables, `lumapi.py`, and product API classes.
- `lumerical_launch_gui_tool`: launch the launcher or a specific product GUI.
- `lumerical_open_session_tool`: open a persistent session for `fdtd`, `mode`, `interconnect`, or `device`.
- `lumerical_eval_script_tool`: run Lumerical script in that session.
- `lumerical_eval_script_get_tool`: run script and return a named variable.
- `lumerical_get_variable_tool` / `lumerical_put_variable_tool`: move variables between MCP client and Lumerical.
- `lumerical_load_project_tool` / `lumerical_save_project_tool`: load and save projects.
- `lumerical_run_script_file_tool`: run an `.lsf` script file.
- `lumerical_run_simulation_tool`: call `run;`.
- `lumerical_close_session_tool`: close a session.
- `lumerical_list_sessions_tool`: list open server-side sessions.
- `lumerical_command_docs_tool`: search bundled command docs from Lumerical's `docs.json`.

Backward-compatible FDTD tool names such as `fdtd_open_session_tool` and `fdtd_eval_script_tool` remain exposed.

## Requirements

- Windows with Ansys Lumerical installed.
- Python 3.10 or newer.
- An MCP-capable client.

The default example path targets:

```text
D:\Program Files\Lumerical\v202
```

Change the environment variables if your installation is elsewhere.

## Install

From this folder:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -e .
```

Copy `.env.example` to `.env` and edit paths if needed:

```powershell
Copy-Item .env.example .env
```

## Codex MCP Config

Add a server entry like this to your Codex MCP configuration:

```toml
[mcp_servers.lumerical]
command = "C:\\path\\to\\lumerical-fdtd-mcp\\.venv\\Scripts\\python.exe"
args = ["C:\\path\\to\\lumerical-fdtd-mcp\\server.py"]
cwd = "C:\\path\\to\\lumerical-fdtd-mcp"

[mcp_servers.lumerical.env]
LUMERICAL_ROOT = "D:\\Program Files\\Lumerical\\v202"
LUMERICAL_LAUNCHER = "D:\\Program Files\\Lumerical\\v202\\bin\\launcher.exe"
LUMERICAL_FDTD_EXE = "D:\\Program Files\\Lumerical\\v202\\bin\\fdtd-solutions.exe"
LUMERICAL_MODE_EXE = "D:\\Program Files\\Lumerical\\v202\\bin\\mode-solutions.exe"
LUMERICAL_INTERCONNECT_EXE = "D:\\Program Files\\Lumerical\\v202\\bin\\interconnect.exe"
LUMERICAL_DEVICE_EXE = "D:\\Program Files\\Lumerical\\v202\\bin\\device.exe"
PYTHONWARNINGS = "ignore"
```

Restart the MCP client after changing the configuration.

## Smoke Test

After the MCP server is available:

1. Run `lumerical_detect_tool`.
2. Run `lumerical_open_session_tool` with `product=fdtd` and `hide=true`.
3. Run `lumerical_eval_script_get_tool` with:

```text
code: mcp_x=2+3;
return_var: mcp_x
```

Expected returned value:

```text
5
```

Then close the session with `lumerical_close_session_tool`.

## Demo Projects

Create minimal verified projects for all supported products:

```powershell
python examples\create_demo_projects.py --launch
```

This creates:

- `examples/demo_projects/demo_fdtd_si_nanoblock.fsp`
- `examples/demo_projects/demo_mode_si_waveguide.lms`
- `examples/demo_projects/demo_interconnect_laser_waveguide.icp`
- `examples/demo_projects/demo_device_charge_region.ldev`

Use `--visible-create` if you want the API creation sessions themselves to be visible.

## Notes

This project does not include Ansys Lumerical binaries, licenses, solver output, or private local configuration. It only provides the MCP bridge code and small reproducible demo scripts.
