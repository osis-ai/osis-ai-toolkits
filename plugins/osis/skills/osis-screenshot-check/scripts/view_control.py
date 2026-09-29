"""准备 OSIS 检查视角并记录本次运行的视图命令。"""

from __future__ import annotations

import argparse
import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


RUN_ID_PATTERN = re.compile(r"^run_\d{8}_\d{6}$")
AUDIT_NAME = "view-command.json"
FRONT_COMMANDS = ["plsm, 1", "/control,view,front", "replot"]


class ViewControlError(RuntimeError):
    """OSIS 视图准备无法安全完成。"""


def _absolute_path(path: str | Path, label: str) -> Path:
    candidate = Path(path)
    text = str(candidate).replace("/", "\\")
    if text.startswith(("\\\\?\\", "\\\\.\\", "\\\\")):
        raise ValueError(f"{label} 不得使用 UNC 或设备路径")
    if not candidate.is_absolute():
        raise ValueError(f"{label} 必须使用绝对路径")
    return candidate.resolve()


def validate_project_run_dir(
    project_dir: str | Path,
    run_dir: str | Path,
) -> tuple[Path, Path]:
    project = _absolute_path(project_dir, "Project directory")
    run = _absolute_path(run_dir, "Run directory")
    if not project.is_dir():
        raise ValueError(f"Project directory is not a directory: {project}")
    expected_parent = (project / "runs" / "osis-screenshot-check").resolve()
    if run.parent != expected_parent or not RUN_ID_PATTERN.fullmatch(run.name):
        raise ValueError(
            "运行目录越界；必须位于项目目录内的 "
            "runs/osis-screenshot-check/run_YYYYMMDD_HHMMSS"
        )
    run.mkdir(parents=True, exist_ok=True)
    resolved_run = run.resolve()
    if project not in resolved_run.parents or resolved_run.parent != expected_parent:
        raise ValueError(f"运行目录越界；必须位于项目目录内: {resolved_run}")
    if not os.access(resolved_run, os.W_OK):
        raise ValueError(f"Run directory is not writable: {resolved_run}")
    return project, resolved_run


def _load_engine() -> Any:
    try:
        from pyosis import OSISEngine

        return OSISEngine()
    except Exception as error:
        raise ViewControlError(f"无法加载 pyosis/OSISEngine: {error}") from error


def _active_project(engine: Any) -> Path:
    try:
        value = engine.project.get_directory()
    except Exception as error:
        raise ViewControlError(f"无法读取当前 OSIS 项目目录: {error}") from error
    if value is None or not str(value).strip():
        raise ViewControlError("当前 OSIS 项目目录为空")
    active = _absolute_path(str(value), "当前 OSIS 项目目录")
    if not active.is_dir():
        raise ViewControlError(f"当前 OSIS 项目目录不存在或不是目录: {active}")
    return active


def _timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _read_audit(path: Path, project: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "schema_version": 1,
            "project_dir": str(project),
            "attempts": [],
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ViewControlError(f"无法读取既有视图审计: {error}") from error
    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != 1
        or payload.get("project_dir") != str(project)
        or not isinstance(payload.get("attempts"), list)
    ):
        raise ViewControlError("既有视图审计与当前项目或格式不一致")
    return payload


def _publish_audit(path: Path, payload: dict[str, Any], run_dir: Path) -> None:
    temporary = run_dir / f".{path.name}.{uuid.uuid4().hex}.tmp"
    try:
        serialized = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        with temporary.open("xb") as stream:
            stream.write(serialized)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except OSError as error:
        raise ViewControlError(f"无法写入视图审计: {error}") from error
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def prepare_view(
    *,
    project_dir: str | Path,
    run_dir: str | Path,
    preset: str = "front",
    engine: Any | None = None,
    clock: Callable[[], str] = _timestamp,
) -> dict[str, Any]:
    """执行一个受支持的视图预设，并追加写入视图审计。"""

    project, run = validate_project_run_dir(project_dir, run_dir)
    if preset != "front":
        raise ValueError(f"Unsupported view preset: {preset}")
    audit_path = run / AUDIT_NAME
    audit = _read_audit(audit_path, project)
    result: dict[str, Any] = {
        "attempt": len(audit["attempts"]) + 1,
        "execution_status": "blocked",
        "view_status": "blocked",
        "view_preset": preset,
        "commands": list(FRONT_COMMANDS),
        "executed_commands": [],
        "timestamp": clock(),
    }

    try:
        active_engine = engine if engine is not None else _load_engine()
        active = _active_project(active_engine)
        if active != project:
            raise ValueError(
                f"传入项目目录与当前 OSIS 项目目录不一致: {project} != {active}"
            )
    except Exception as error:
        result["failed_step"] = "validate_active_project"
        result["error"] = str(error)
    else:
        steps = (
            ("plsm, 1", lambda: active_engine.run("plsm, 1")),
            (
                "/control,view,front",
                lambda: active_engine.run("/control,view,front"),
            ),
            ("replot", active_engine.replot),
        )
        for label, operation in steps:
            try:
                operation()
            except Exception as error:
                result["failed_step"] = label
                result["error"] = str(error)
                break
            result["executed_commands"].append(label)
        else:
            result["execution_status"] = "completed"
            result["view_status"] = "prepared"

    audit["attempts"].append(result)
    _publish_audit(audit_path, audit, run)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="准备 OSIS 截图检查视角")
    subcommands = parser.add_subparsers(dest="command", required=True)
    prepare = subcommands.add_parser("prepare")
    prepare.add_argument("--preset", default="front", choices=("front",))
    prepare.add_argument("--project-dir", required=True)
    prepare.add_argument("--run-dir", required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        result = prepare_view(
            project_dir=args.project_dir,
            run_dir=args.run_dir,
            preset=args.preset,
        )
    except Exception as error:
        result = {
            "execution_status": "blocked",
            "view_status": "blocked",
            "view_preset": getattr(args, "preset", None),
            "error": str(error),
        }
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("view_status") == "prepared" else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "AUDIT_NAME",
    "FRONT_COMMANDS",
    "ViewControlError",
    "prepare_view",
    "validate_project_run_dir",
]
