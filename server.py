from __future__ import annotations

import logging
import os
import warnings

from dotenv import load_dotenv

os.environ.setdefault("PYTHONWARNINGS", "ignore")
warnings.simplefilter("ignore")
logging.getLogger().setLevel(logging.ERROR)

from fastmcp import FastMCP

from tools.lumerical_bridge import (
    close_session,
    command_docs,
    detect_environment,
    eval_script,
    eval_script_get,
    get_variable,
    launch_gui,
    list_gui_jobs,
    list_sessions,
    load_project,
    open_session,
    put_variable,
    run_script_file,
    run_simulation,
    save_project,
)


load_dotenv()

mcp = FastMCP("Lumerical Multi-Product MCP")


@mcp.tool()
def lumerical_detect_tool() -> dict:
    """Detect Lumerical executables, lumapi.py, and API support for FDTD/MODE/INTERCONNECT/DEVICE."""
    return detect_environment()


@mcp.tool()
def lumerical_launch_gui_tool(
    target: str = "launcher",
    project_path: str | None = None,
    extra_args: list[str] | None = None,
) -> dict:
    """Launch the Lumerical launcher or a product GUI. target: launcher, fdtd, mode, interconnect, or device."""
    return launch_gui(target=target, project_path=project_path, extra_args=extra_args)


@mcp.tool()
def lumerical_gui_jobs_tool() -> dict:
    """List GUI processes launched by this MCP server."""
    return list_gui_jobs()


@mcp.tool()
def lumerical_open_session_tool(
    product: str = "fdtd",
    session_id: str = "default",
    filename: str | None = None,
    hide: bool = False,
    server_args: dict | None = None,
) -> dict:
    """Open a persistent lumapi session for fdtd, mode, interconnect, or device."""
    return open_session(
        product=product,
        session_id=session_id,
        filename=filename,
        hide=hide,
        server_args=server_args,
    )


@mcp.tool()
def lumerical_list_sessions_tool() -> dict:
    """List Lumerical API sessions held by this MCP server."""
    return list_sessions()


@mcp.tool()
def lumerical_close_session_tool(session_id: str = "default") -> dict:
    """Close a persistent Lumerical API session."""
    return close_session(session_id=session_id)


@mcp.tool()
def lumerical_eval_script_tool(code: str, session_id: str = "default") -> dict:
    """Execute Lumerical script code inside an open session."""
    return eval_script(session_id=session_id, code=code)


@mcp.tool()
def lumerical_eval_script_get_tool(
    code: str,
    return_var: str,
    session_id: str = "default",
    max_array_items: int = 2000,
) -> dict:
    """Execute Lumerical script code, then return a named variable to Codex."""
    return eval_script_get(
        session_id=session_id,
        code=code,
        return_var=return_var,
        max_array_items=max_array_items,
    )


@mcp.tool()
def lumerical_get_variable_tool(name: str, session_id: str = "default", max_array_items: int = 2000) -> dict:
    """Get a variable from the Lumerical script workspace."""
    return get_variable(session_id=session_id, name=name, max_array_items=max_array_items)


@mcp.tool()
def lumerical_put_variable_tool(name: str, value, session_id: str = "default") -> dict:
    """Put a JSON-compatible variable into the Lumerical script workspace."""
    return put_variable(session_id=session_id, name=name, value=value)


@mcp.tool()
def lumerical_load_project_tool(project_path: str, session_id: str = "default") -> dict:
    """Load a Lumerical project into an open session."""
    return load_project(session_id=session_id, project_path=project_path)


@mcp.tool()
def lumerical_save_project_tool(project_path: str | None = None, session_id: str = "default") -> dict:
    """Save the current Lumerical project, optionally to a new project path."""
    return save_project(session_id=session_id, project_path=project_path)


@mcp.tool()
def lumerical_run_script_file_tool(script_path: str, session_id: str = "default") -> dict:
    """Run a Lumerical script file in an open session."""
    return run_script_file(session_id=session_id, script_path=script_path)


@mcp.tool()
def lumerical_run_simulation_tool(session_id: str = "default") -> dict:
    """Run the current Lumerical simulation by executing `run;`."""
    return run_simulation(session_id=session_id)


@mcp.tool()
def lumerical_command_docs_tool(query: str | None = None, limit: int = 50) -> dict:
    """Search bundled Lumerical command documentation from docs.json."""
    return command_docs(query=query, limit=limit)


# Backward-compatible FDTD tool names.


@mcp.tool()
def fdtd_detect_tool() -> dict:
    """Detect Lumerical FDTD executables, lumapi.py, and Python API import status."""
    return detect_environment()


@mcp.tool()
def fdtd_launch_gui_tool(
    target: str = "fdtd",
    project_path: str | None = None,
    extra_args: list[str] | None = None,
) -> dict:
    """Launch the Lumerical launcher or FDTD Solutions GUI without opening an API session."""
    return launch_gui(target=target, project_path=project_path, extra_args=extra_args)


@mcp.tool()
def fdtd_gui_jobs_tool() -> dict:
    """List GUI processes launched by this MCP server."""
    return list_gui_jobs()


@mcp.tool()
def fdtd_open_session_tool(
    session_id: str = "default",
    filename: str | None = None,
    hide: bool = False,
    server_args: dict | None = None,
) -> dict:
    """Open a persistent lumapi.FDTD session, optionally loading an .fsp or running an .lsf file."""
    return open_session(
        product="fdtd",
        session_id=session_id,
        filename=filename,
        hide=hide,
        server_args=server_args,
    )


@mcp.tool()
def fdtd_list_sessions_tool() -> dict:
    """List Lumerical API sessions held by this MCP server."""
    return list_sessions()


@mcp.tool()
def fdtd_close_session_tool(session_id: str = "default") -> dict:
    """Close a persistent FDTD API session."""
    return close_session(session_id=session_id)


@mcp.tool()
def fdtd_eval_script_tool(code: str, session_id: str = "default") -> dict:
    """Execute Lumerical script code inside an open FDTD session."""
    return eval_script(session_id=session_id, code=code)


@mcp.tool()
def fdtd_eval_script_get_tool(
    code: str,
    return_var: str,
    session_id: str = "default",
    max_array_items: int = 2000,
) -> dict:
    """Execute Lumerical script code, then return a named variable to Codex."""
    return eval_script_get(
        session_id=session_id,
        code=code,
        return_var=return_var,
        max_array_items=max_array_items,
    )


@mcp.tool()
def fdtd_get_variable_tool(name: str, session_id: str = "default", max_array_items: int = 2000) -> dict:
    """Get a variable from the FDTD script workspace."""
    return get_variable(session_id=session_id, name=name, max_array_items=max_array_items)


@mcp.tool()
def fdtd_put_variable_tool(name: str, value, session_id: str = "default") -> dict:
    """Put a JSON-compatible variable into the FDTD script workspace."""
    return put_variable(session_id=session_id, name=name, value=value)


@mcp.tool()
def fdtd_load_project_tool(project_path: str, session_id: str = "default") -> dict:
    """Load an FDTD .fsp project into an open session."""
    return load_project(session_id=session_id, project_path=project_path)


@mcp.tool()
def fdtd_save_project_tool(project_path: str | None = None, session_id: str = "default") -> dict:
    """Save the current FDTD project, optionally to a new .fsp path."""
    return save_project(session_id=session_id, project_path=project_path)


@mcp.tool()
def fdtd_run_script_file_tool(script_path: str, session_id: str = "default") -> dict:
    """Run a Lumerical script file in an open FDTD session."""
    return run_script_file(session_id=session_id, script_path=script_path)


@mcp.tool()
def fdtd_run_simulation_tool(session_id: str = "default") -> dict:
    """Run the current FDTD simulation by executing `run;`."""
    return run_simulation(session_id=session_id)


@mcp.tool()
def fdtd_command_docs_tool(query: str | None = None, limit: int = 50) -> dict:
    """Search bundled Lumerical command documentation from docs.json."""
    return command_docs(query=query, limit=limit)


if __name__ == "__main__":
    mcp.run(show_banner=False, log_level="ERROR")
