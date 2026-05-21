from __future__ import annotations

import json
from pathlib import Path
import sys
import traceback
import warnings

warnings.simplefilter("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import lumerical_bridge as bridge


DISPATCH = {
    "detect_environment": bridge._direct_detect_environment,
    "open_session": bridge._direct_open_session,
    "list_sessions": bridge._direct_list_sessions,
    "close_session": bridge._direct_close_session,
    "eval_script": bridge._direct_eval_script,
    "eval_script_get": bridge._direct_eval_script_get,
    "get_variable": bridge._direct_get_variable,
    "put_variable": bridge._direct_put_variable,
    "load_project": bridge._direct_load_project,
    "save_project": bridge._direct_save_project,
    "run_script_file": bridge._direct_run_script_file,
    "run_simulation": bridge._direct_run_simulation,
}


def _write(response: dict) -> None:
    sys.stdout.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def main() -> int:
    for line in sys.stdin:
        try:
            request = json.loads(line)
            action = request.get("action")
            payload = request.get("payload") or {}
            if action not in DISPATCH:
                raise ValueError(f"Unknown worker action: {action}")
            result = DISPATCH[action](**payload)
            _write({"ok": True, "result": result})
        except Exception as exc:
            _write(
                {
                    "ok": False,
                    "error": f"{type(exc).__name__}: {exc}",
                    "traceback": traceback.format_exc(limit=12),
                }
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
