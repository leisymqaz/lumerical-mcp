from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any


DEFAULT_LUMERICAL_ROOT = r"D:\Program Files\Lumerical\v202"
_DLL_DIRECTORY_HANDLES: list[Any] = []
_DLL_DIRECTORY_PATHS: set[str] = set()
_LUMAPI_MODULE: Any | None = None
_SESSIONS: dict[str, Any] = {}
_SESSION_INFO: dict[str, dict[str, Any]] = {}
_JOBS: dict[str, dict[str, Any]] = {}
_LOCK = threading.RLock()
_WORKER_LOCK = threading.RLock()
_WORKER_PROCESS: subprocess.Popen[str] | None = None


PRODUCTS: dict[str, dict[str, str]] = {
    "fdtd": {
        "class": "FDTD",
        "exe_env": "LUMERICAL_FDTD_EXE",
        "exe_name": "fdtd-solutions.exe",
        "extension": ".fsp",
    },
    "mode": {
        "class": "MODE",
        "exe_env": "LUMERICAL_MODE_EXE",
        "exe_name": "mode-solutions.exe",
        "extension": ".lms",
    },
    "interconnect": {
        "class": "INTERCONNECT",
        "exe_env": "LUMERICAL_INTERCONNECT_EXE",
        "exe_name": "interconnect.exe",
        "extension": ".icp",
    },
    "device": {
        "class": "DEVICE",
        "exe_env": "LUMERICAL_DEVICE_EXE",
        "exe_name": "device.exe",
        "extension": ".ldev",
    },
}


def _normalize_product(product: str | None) -> str:
    normalized = (product or "fdtd").strip().lower()
    aliases = {
        "fdtd-solutions": "fdtd",
        "mode-solutions": "mode",
        "intc": "interconnect",
        "interconnect-solutions": "interconnect",
        "charge": "device",
        "heat": "device",
        "dgtd": "device",
        "feem": "device",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in PRODUCTS:
        raise ValueError(f"Unknown Lumerical product '{product}'. Use one of: {', '.join(PRODUCTS)}")
    return normalized


def _configured_root() -> Path:
    root = os.environ.get("LUMERICAL_ROOT")
    if root:
        return Path(root)
    launcher = os.environ.get("LUMERICAL_LAUNCHER")
    if launcher:
        launcher_path = Path(launcher)
        if launcher_path.name.lower() == "launcher.exe":
            return launcher_path.parent.parent
    return Path(DEFAULT_LUMERICAL_ROOT)


def _paths() -> dict[str, Any]:
    root = _configured_root()
    bin_dir = root / "bin"
    products: dict[str, dict[str, Path | str]] = {}
    for name, spec in PRODUCTS.items():
        products[name] = {
            **spec,
            "exe": Path(os.environ.get(spec["exe_env"], str(bin_dir / spec["exe_name"]))),
        }
    return {
        "root": root,
        "api_python": root / "api" / "python",
        "lumapi": root / "api" / "python" / "lumapi.py",
        "bin": bin_dir,
        "launcher": Path(os.environ.get("LUMERICAL_LAUNCHER", str(bin_dir / "launcher.exe"))),
        "products": products,
        "fdtd_exe": products["fdtd"]["exe"],
        "fdtd_engine": bin_dir / "fdtd-engine.exe",
    }


def _path_status(path: Path) -> dict[str, Any]:
    try:
        stat = path.stat()
        return {"path": str(path), "exists": True, "size": stat.st_size, "mtime": stat.st_mtime}
    except FileNotFoundError:
        return {"path": str(path), "exists": False}


def _prepare_lumapi_import() -> dict[str, Any]:
    paths = _paths()
    for directory in (paths["api_python"], paths["bin"]):
        if directory.exists():
            path_string = str(directory)
            if path_string not in sys.path:
                sys.path.insert(0, path_string)
            if hasattr(os, "add_dll_directory") and path_string not in _DLL_DIRECTORY_PATHS:
                try:
                    handle = os.add_dll_directory(path_string)
                    _DLL_DIRECTORY_HANDLES.append(handle)
                    _DLL_DIRECTORY_PATHS.add(path_string)
                except OSError:
                    pass

    product_paths = {
        name: {
            "class": spec["class"],
            "extension": spec["extension"],
            "exe": _path_status(spec["exe"]),
        }
        for name, spec in paths["products"].items()
    }
    return {
        "root": _path_status(paths["root"]),
        "api_python": _path_status(paths["api_python"]),
        "lumapi": _path_status(paths["lumapi"]),
        "bin": _path_status(paths["bin"]),
        "launcher": _path_status(paths["launcher"]),
        "products": product_paths,
        "fdtd_exe": _path_status(paths["fdtd_exe"]),
        "fdtd_engine": _path_status(paths["fdtd_engine"]),
    }


def _import_lumapi() -> Any:
    global _LUMAPI_MODULE
    if _LUMAPI_MODULE is not None:
        return _LUMAPI_MODULE
    _prepare_lumapi_import()
    import lumapi  # type: ignore

    _LUMAPI_MODULE = lumapi
    return lumapi


def _jsonable(value: Any, max_array_items: int = 2000) -> Any:
    try:
        import numpy as np
    except Exception:
        np = None  # type: ignore

    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, complex):
        return {"real": value.real, "imag": value.imag}
    if np is not None:
        if isinstance(value, np.generic):
            return _jsonable(value.item())
        if isinstance(value, np.ndarray):
            flat_size = int(value.size)
            if flat_size <= max_array_items:
                return {
                    "type": "ndarray",
                    "shape": list(value.shape),
                    "dtype": str(value.dtype),
                    "data": _jsonable(value.tolist(), max_array_items=max_array_items),
                }
            flat = value.ravel()
            return {
                "type": "ndarray",
                "shape": list(value.shape),
                "dtype": str(value.dtype),
                "size": flat_size,
                "sample": _jsonable(flat[: min(20, flat_size)].tolist(), max_array_items=max_array_items),
                "truncated": True,
            }
    if isinstance(value, dict):
        return {str(k): _jsonable(v, max_array_items=max_array_items) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item, max_array_items=max_array_items) for item in value]
    return repr(value)


def detect_environment() -> dict[str, Any]:
    prepared = _prepare_lumapi_import()
    result: dict[str, Any] = {
        "ok": False,
        "paths": prepared,
        "python": sys.executable,
        "env": {
            "LUMERICAL_ROOT": os.environ.get("LUMERICAL_ROOT"),
            "LUMERICAL_LAUNCHER": os.environ.get("LUMERICAL_LAUNCHER"),
            **{spec["exe_env"]: os.environ.get(spec["exe_env"]) for spec in PRODUCTS.values()},
        },
        "lumapi_importable": False,
        "products": {},
    }
    try:
        lumapi = _import_lumapi()
        result["lumapi_importable"] = True
        result["lumapi_file"] = getattr(lumapi, "__file__", None)
        for product, spec in PRODUCTS.items():
            class_exists = hasattr(lumapi, spec["class"])
            exe_exists = prepared["products"][product]["exe"]["exists"]
            result["products"][product] = {
                "class": spec["class"],
                "class_available": class_exists,
                "exe_available": exe_exists,
                "extension": spec["extension"],
                "ok": bool(class_exists and exe_exists),
            }
        result["has_fdtd_class"] = result["products"]["fdtd"]["class_available"]
        result["ok"] = prepared["launcher"]["exists"] and all(p["ok"] for p in result["products"].values())
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def launch_gui(
    target: str = "launcher",
    project_path: str | None = None,
    extra_args: list[str] | None = None,
) -> dict[str, Any]:
    paths = _paths()
    normalized_target = (target or "launcher").strip().lower()
    if normalized_target in {"launcher", "launch"}:
        exe = paths["launcher"]
        kind = "launcher"
    else:
        product = _normalize_product(normalized_target)
        exe = paths["products"][product]["exe"]
        kind = product
    if not exe.exists():
        return {"ok": False, "error": f"Executable not found: {exe}"}

    args = [str(exe)]
    if project_path:
        args.append(str(Path(project_path)))
    if extra_args:
        args.extend(extra_args)

    process = subprocess.Popen(
        args,
        cwd=str(paths["bin"]) if paths["bin"].exists() else None,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )
    job_id = f"lumerical-{kind}-gui-{uuid.uuid4().hex[:10]}"
    _JOBS[job_id] = {
        "id": job_id,
        "kind": kind,
        "args": args,
        "pid": process.pid,
        "started_at": time.time(),
        "process": process,
    }
    return {"ok": True, "job_id": job_id, "pid": process.pid, "args": args}


def _session_or_error(session_id: str = "default", product: str | None = None) -> Any:
    with _LOCK:
        session = _SESSIONS.get(session_id)
        info = _SESSION_INFO.get(session_id)
        if session is None or info is None:
            raise RuntimeError(f"Lumerical session '{session_id}' is not open. Call lumerical_open_session_tool first.")
        if product is not None and info.get("product") != _normalize_product(product):
            raise RuntimeError(
                f"Session '{session_id}' is a {info.get('product')} session, not {product}."
            )
        return session


def open_session(
    session_id: str = "default",
    filename: str | None = None,
    hide: bool = False,
    server_args: dict[str, Any] | None = None,
    product: str = "fdtd",
) -> dict[str, Any]:
    product = _normalize_product(product)
    lumapi = _import_lumapi()
    class_name = PRODUCTS[product]["class"]
    cls = getattr(lumapi, class_name)
    with _LOCK:
        if session_id in _SESSIONS:
            info = _SESSION_INFO[session_id]
            if info.get("product") != product:
                raise RuntimeError(
                    f"Session '{session_id}' already exists as {info.get('product')}; requested {product}."
                )
            return {"ok": True, "session_id": session_id, "already_open": True, "info": info}
        session = cls(filename=filename, hide=hide, serverArgs=server_args or {})
        _SESSIONS[session_id] = session
        _SESSION_INFO[session_id] = {
            "session_id": session_id,
            "product": product,
            "class": class_name,
            "filename": filename,
            "hide": hide,
            "opened_at": time.time(),
        }
    return {"ok": True, "session_id": session_id, "info": _SESSION_INFO[session_id]}


def list_sessions() -> dict[str, Any]:
    with _LOCK:
        return {"ok": True, "sessions": list(_SESSION_INFO.values())}


def close_session(session_id: str = "default") -> dict[str, Any]:
    with _LOCK:
        session = _SESSIONS.pop(session_id, None)
        info = _SESSION_INFO.pop(session_id, None)
    if session is None:
        return {"ok": True, "session_id": session_id, "already_closed": True}
    session.close()
    return {"ok": True, "session_id": session_id, "closed": info}


def eval_script(session_id: str, code: str) -> dict[str, Any]:
    session = _session_or_error(session_id)
    session.eval(code)
    return {"ok": True, "session_id": session_id}


def eval_script_get(session_id: str, code: str, return_var: str, max_array_items: int = 2000) -> dict[str, Any]:
    session = _session_or_error(session_id)
    session.eval(code)
    value = session.getv(return_var)
    return {"ok": True, "session_id": session_id, "variable": return_var, "value": _jsonable(value, max_array_items)}


def get_variable(session_id: str, name: str, max_array_items: int = 2000) -> dict[str, Any]:
    session = _session_or_error(session_id)
    value = session.getv(name)
    return {"ok": True, "session_id": session_id, "variable": name, "value": _jsonable(value, max_array_items)}


def put_variable(session_id: str, name: str, value: Any) -> dict[str, Any]:
    session = _session_or_error(session_id)
    session.putv(name, value)
    return {"ok": True, "session_id": session_id, "variable": name}


def load_project(session_id: str, project_path: str) -> dict[str, Any]:
    session = _session_or_error(session_id)
    path = str(Path(project_path))
    session.load(path)
    _SESSION_INFO.setdefault(session_id, {})["filename"] = path
    return {"ok": True, "session_id": session_id, "project_path": path}


def save_project(session_id: str, project_path: str | None = None) -> dict[str, Any]:
    session = _session_or_error(session_id)
    if project_path:
        path = str(Path(project_path))
        session.save(path)
        _SESSION_INFO.setdefault(session_id, {})["filename"] = path
    else:
        session.save()
        path = _SESSION_INFO.get(session_id, {}).get("filename")
    return {"ok": True, "session_id": session_id, "project_path": path}


def run_script_file(session_id: str, script_path: str) -> dict[str, Any]:
    session = _session_or_error(session_id)
    path = str(Path(script_path))
    if path.lower().endswith(".lsfx"):
        session.eval(path[:-5] + ";")
    else:
        session.feval(path)
    return {"ok": True, "session_id": session_id, "script_path": path}


def run_simulation(session_id: str = "default") -> dict[str, Any]:
    session = _session_or_error(session_id)
    started_at = time.time()
    session.eval("run;")
    return {"ok": True, "session_id": session_id, "elapsed_seconds": time.time() - started_at}


def list_gui_jobs() -> dict[str, Any]:
    jobs = []
    for job_id, job in list(_JOBS.items()):
        process = job["process"]
        poll = process.poll()
        jobs.append(
            {
                "id": job_id,
                "kind": job["kind"],
                "pid": job["pid"],
                "args": job["args"],
                "started_at": job["started_at"],
                "running": poll is None,
                "returncode": poll,
            }
        )
    return {"ok": True, "jobs": jobs}


def command_docs(query: str | None = None, limit: int = 50) -> dict[str, Any]:
    paths = _paths()
    docs_path = paths["api_python"] / "docs.json"
    if not docs_path.exists():
        return {"ok": False, "error": f"docs.json not found: {docs_path}"}
    docs = json.loads(docs_path.read_text(encoding="utf-8", errors="replace"))
    items = []
    needle = query.lower() if query else None
    for name, doc in docs.items():
        haystack = f"{name}\n{doc.get('text', '')}".lower()
        if needle and needle not in haystack:
            continue
        items.append({"name": name, "text": doc.get("text", ""), "link": doc.get("link", "")})
        if len(items) >= limit:
            break
    return {"ok": True, "count": len(items), "commands": items}


_direct_detect_environment = detect_environment
_direct_open_session = open_session
_direct_list_sessions = list_sessions
_direct_close_session = close_session
_direct_eval_script = eval_script
_direct_eval_script_get = eval_script_get
_direct_get_variable = get_variable
_direct_put_variable = put_variable
_direct_load_project = load_project
_direct_save_project = save_project
_direct_run_script_file = run_script_file
_direct_run_simulation = run_simulation


def _worker_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTHONWARNINGS", "ignore")
    paths = _paths()
    env.setdefault("LUMERICAL_ROOT", str(paths["root"]))
    env.setdefault("LUMERICAL_LAUNCHER", str(paths["launcher"]))
    for product, spec in paths["products"].items():
        env.setdefault(PRODUCTS[product]["exe_env"], str(spec["exe"]))
    return env


def _ensure_worker() -> subprocess.Popen[str]:
    global _WORKER_PROCESS
    if _WORKER_PROCESS is not None and _WORKER_PROCESS.poll() is None:
        return _WORKER_PROCESS
    worker_script = Path(__file__).with_name("fdtd_worker.py")
    _WORKER_PROCESS = subprocess.Popen(
        [sys.executable, str(worker_script)],
        cwd=str(Path(__file__).resolve().parent.parent),
        env=_worker_env(),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        bufsize=1,
    )
    return _WORKER_PROCESS


def _read_worker_line(process: subprocess.Popen[str], timeout: float) -> str:
    if process.stdout is None:
        raise RuntimeError("Lumerical worker stdout is unavailable")
    lines: queue.Queue[str] = queue.Queue(maxsize=1)

    def read_line() -> None:
        try:
            lines.put(process.stdout.readline())
        except Exception:
            lines.put("")

    thread = threading.Thread(target=read_line, daemon=True)
    thread.start()
    try:
        return lines.get(timeout=timeout)
    except queue.Empty as exc:
        process.kill()
        raise TimeoutError(f"Lumerical worker did not respond within {timeout:g} seconds") from exc


def _worker_call(action: str, payload: dict[str, Any] | None = None, timeout: float = 90.0) -> dict[str, Any]:
    global _WORKER_PROCESS
    with _WORKER_LOCK:
        process = _ensure_worker()
        if process.stdin is None:
            raise RuntimeError("Lumerical worker stdio is unavailable")
        request = {"action": action, "payload": payload or {}}
        try:
            process.stdin.write(json.dumps(request, ensure_ascii=False) + "\n")
            process.stdin.flush()
            line = _read_worker_line(process, timeout)
        except BrokenPipeError as exc:
            _WORKER_PROCESS = None
            raise RuntimeError("Lumerical worker exited before handling the request") from exc
        if not line:
            _WORKER_PROCESS = None
            raise RuntimeError("Lumerical worker exited without a response")
        response = json.loads(line)
        if not response.get("ok"):
            raise RuntimeError(response.get("error", "Lumerical worker request failed"))
        return response["result"]


def detect_environment() -> dict[str, Any]:
    return _worker_call("detect_environment")


def open_session(
    session_id: str = "default",
    filename: str | None = None,
    hide: bool = False,
    server_args: dict[str, Any] | None = None,
    product: str = "fdtd",
) -> dict[str, Any]:
    return _worker_call(
        "open_session",
        {
            "session_id": session_id,
            "filename": filename,
            "hide": hide,
            "server_args": server_args,
            "product": product,
        },
    )


def list_sessions() -> dict[str, Any]:
    return _worker_call("list_sessions")


def close_session(session_id: str = "default") -> dict[str, Any]:
    return _worker_call("close_session", {"session_id": session_id})


def eval_script(session_id: str, code: str) -> dict[str, Any]:
    return _worker_call("eval_script", {"session_id": session_id, "code": code})


def eval_script_get(session_id: str, code: str, return_var: str, max_array_items: int = 2000) -> dict[str, Any]:
    return _worker_call(
        "eval_script_get",
        {
            "session_id": session_id,
            "code": code,
            "return_var": return_var,
            "max_array_items": max_array_items,
        },
    )


def get_variable(session_id: str, name: str, max_array_items: int = 2000) -> dict[str, Any]:
    return _worker_call(
        "get_variable",
        {"session_id": session_id, "name": name, "max_array_items": max_array_items},
    )


def put_variable(session_id: str, name: str, value: Any) -> dict[str, Any]:
    return _worker_call("put_variable", {"session_id": session_id, "name": name, "value": value})


def load_project(session_id: str, project_path: str) -> dict[str, Any]:
    return _worker_call("load_project", {"session_id": session_id, "project_path": project_path})


def save_project(session_id: str, project_path: str | None = None) -> dict[str, Any]:
    return _worker_call("save_project", {"session_id": session_id, "project_path": project_path})


def run_script_file(session_id: str, script_path: str) -> dict[str, Any]:
    return _worker_call("run_script_file", {"session_id": session_id, "script_path": script_path})


def run_simulation(session_id: str = "default") -> dict[str, Any]:
    return _worker_call("run_simulation", {"session_id": session_id})
