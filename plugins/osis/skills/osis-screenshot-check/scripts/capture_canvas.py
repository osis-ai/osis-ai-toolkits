"""通过原生 UIA 定位 OSIS 画布，并用 WGC 写入项目运行目录。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import struct
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Mapping

from PIL import Image, ImageChops


DEFAULT_CANVAS_NAME = "3D绘图"
DEFAULT_PROCESS_NAME = "Osis"
DEFAULT_TIMEOUT = 30.0
RUN_ID_PATTERN = re.compile(r"^run_\d{8}_\d{6}$")
AUTO_BODY_PADDING = 12
MIN_FOREGROUND_HEIGHT_RATIO = 0.30
BACKGROUND_TOLERANCE = 8
PRIMARY_BAND_MIN_WIDTH_RATIO = 0.50
PRIMARY_BAND_MIN_ASPECT_RATIO = 3.0
PRIMARY_BAND_MIN_CENTER_Y_RATIO = 0.15
PRIMARY_BAND_MAX_CENTER_Y_RATIO = 0.90
PRIMARY_BAND_DENSE_ROW_RATIO = 0.08
PRIMARY_BAND_DENSE_CLUSTER_GAP_RATIO = 0.01
PRIMARY_BAND_MAX_CHORD_GAP_RATIO = 0.25
PRIMARY_BAND_MAX_CHORD_HEIGHT_RATIO = 0.02
PRIMARY_BAND_CANVAS_EDGE_FACTOR = 0.50
TRIPTYCH_OVERLAP_RATIO = 0.05
VISUAL_VIEW_ORDER = ("full", "left", "middle", "right")
VISUAL_RESULT_VALUES = {
    "incorrect",
    "no_obvious_anomaly",
    "unjudgeable",
}
VISUAL_RESULT_FIELDS = {
    "screening_result",
    "visual_verdict",
    "reviewed_views",
    "issues",
    "summary",
}
VISUAL_ISSUE_FIELDS = {
    "issue_id",
    "issue_type",
    "region",
    "description",
    "bbox_normalized",
}
VISUAL_ISSUE_REGIONS = set(VISUAL_VIEW_ORDER)
VISUAL_PREFIX_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,31}$")
VISUAL_MANIFEST_NAME = "run-manifest.json"
VISUAL_RESULT_INPUT_NAME = "visual-result.json"
PROJECT_PROFILE_RELATIVE = Path("py") / "项目画像.md"
PROJECT_PROFILE_CONTEXT_NAME = "project-profile-context.json"
PROJECT_PROFILE_PRODUCER = "osis-screenshot-check/freeze-profile"


class RealMachineError(RuntimeError):
    """桌面捕获流程无法安全完成。"""


class UnjudgeableError(RealMachineError):
    """输入的语义目标或原生几何不可信。"""


class VisualEvidenceError(UnjudgeableError):
    """截图存在，但主体或像素证据不足以进入视觉筛查。"""


def validate_semantic_identity(identity: Mapping[str, Any]) -> dict[str, str]:
    """校验原生 UIA 返回的窗口与画布身份字段。"""
    if not isinstance(identity, Mapping):
        raise UnjudgeableError("UIA identity must be an object")
    fields = (
        "source",
        "window_title",
        "process_name",
        "canvas_name",
        "window_ref",
        "canvas_ref",
    )
    missing = [field for field in fields if field not in identity]
    if missing:
        raise UnjudgeableError(
            f"UIA identity is missing required fields: {', '.join(missing)}"
        )
    normalized: dict[str, str] = {}
    for field in fields:
        value = identity.get(field)
        if not isinstance(value, str) or not value.strip() or "\x00" in value:
            raise UnjudgeableError(f"Invalid UIA identity field: {field}")
        normalized[field] = value
    if normalized["source"] != "windows-uia":
        raise UnjudgeableError("Identity source must be windows-uia")
    if normalized["window_ref"] == normalized["canvas_ref"]:
        raise UnjudgeableError("Window and canvas references must differ")
    for ref_field, hwnd_field in (
        ("window_ref", "top_hwnd"),
        ("canvas_ref", "canvas_hwnd"),
    ):
        hwnd = identity.get(hwnd_field)
        if hwnd is not None and normalized[ref_field] != f"hwnd:{hwnd}":
            raise UnjudgeableError(f"{ref_field} does not match {hwnd_field}")
    return normalized


def _absolute_path(path: str | Path, label: str) -> Path:
    candidate = Path(path)
    text = str(candidate).replace("/", "\\")
    if text.startswith(("\\\\?\\", "\\\\.\\", "\\\\")):
        raise ValueError(f"{label} 不得使用 UNC 或设备路径")
    if not candidate.is_absolute():
        raise ValueError(f"{label} 必须使用绝对路径")
    return candidate.resolve()


def validate_project_run_dir(
    project_dir: str | Path, run_dir: str | Path, *, create: bool = True
) -> Path:
    project = _absolute_path(project_dir, "Project directory")
    run = _absolute_path(run_dir, "Run directory")
    if not project.is_dir():
        raise ValueError(f"Project directory is not a directory: {project}")
    expected_parent = (project / "runs" / "osis-screenshot-check").resolve()
    if run.parent != expected_parent or not RUN_ID_PATTERN.fullmatch(run.name):
        raise ValueError("运行目录越界；必须位于项目目录内的 runs/osis-screenshot-check/run_YYYYMMDD_HHMMSS")
    if create:
        try:
            run.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise ValueError(f"Cannot create run directory {run}: {error}") from error
    resolved_run = run.resolve()
    if project not in resolved_run.parents or resolved_run.parent != expected_parent:
        raise ValueError(f"运行目录越界；必须位于项目目录内: {resolved_run}")
    if create and (not resolved_run.is_dir() or not os.access(resolved_run, os.W_OK)):
        raise ValueError(f"Run directory is not writable: {resolved_run}")
    return resolved_run


def validate_artifact_path(path: str | Path, run_dir: str | Path, *, suffix: str) -> Path:
    artifact = _absolute_path(path, "Artifact path")
    root = _absolute_path(run_dir, "Run directory")
    if artifact == root or root not in artifact.parents:
        raise ValueError(f"产物路径必须位于运行目录内: {root}")
    if artifact.suffix.lower() != suffix.lower():
        raise ValueError(f"产物路径必须是 {suffix.removeprefix('.').upper()} 文件")
    return artifact


def validate_capture_path(path: str | Path, run_dir: str | Path) -> Path:
    return validate_artifact_path(path, run_dir, suffix=".png")


def _read_png_size(path: Path) -> tuple[int, int]:
    try:
        with path.open("rb") as stream:
            header = stream.read(24)
    except OSError as error:
        raise UnjudgeableError(f"Cannot read capture output: {error}") from error
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise UnjudgeableError("Capture backend did not write a valid PNG")
    width, height = struct.unpack(">II", header[16:24])
    if width <= 0 or height <= 0:
        raise UnjudgeableError("Capture image dimensions are invalid")
    return width, height


def _serialize_json(payload: Mapping[str, Any]) -> bytes:
    try:
        return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise RealMachineError(f"Cannot serialize JSON metadata: {error}") from error


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise UnjudgeableError(f"Cannot hash evidence image: {error}") from error
    return digest.hexdigest()


def _read_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as stream:
            payload = json.load(stream)
    except (OSError, json.JSONDecodeError) as error:
        raise VisualEvidenceError(f"Cannot read {label}: {error}") from error
    if not isinstance(payload, dict):
        raise VisualEvidenceError(f"{label} must contain a JSON object")
    return payload


def _unknown_field(
    value: Mapping[str, Any],
    allowed: set[str],
    path: str,
) -> str | None:
    for key in value:
        if not isinstance(key, str) or key not in allowed:
            return f"{path}.{key}"
    return None


def _validate_fixed_run_json(
    value: str | Path,
    run_dir: Path,
    expected_name: str,
    *,
    must_exist: bool,
) -> Path:
    literal = Path(value)
    if literal.is_symlink():
        raise VisualEvidenceError(
            f"{expected_name} must not be a symbolic link"
        )
    path = validate_artifact_path(literal, run_dir, suffix=".json")
    expected = (run_dir / expected_name).resolve()
    if path != expected:
        raise ValueError(f"JSON artifact must be {expected_name}")
    if must_exist and (not literal.is_file() or not path.is_file()):
        raise VisualEvidenceError(f"{expected_name} must be a regular file")
    return path


def _profile_context_sha256(payload: Mapping[str, Any]) -> str:
    core = {
        key: value
        for key, value in payload.items()
        if key != "context_sha256"
    }
    serialized = json.dumps(
        core,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def _validate_project_profile_payload(
    payload: Mapping[str, Any],
    project_dir: Path,
    *,
    require_current: bool,
) -> dict[str, Any]:
    required = {
        "schema_version",
        "producer",
        "project_dir",
        "source_path",
        "source_sha256",
        "frozen_text",
        "context_sha256",
    }
    project = project_dir.resolve()
    source_literal = project / PROJECT_PROFILE_RELATIVE
    source = source_literal.resolve()
    if (
        set(payload) != required
        or payload.get("schema_version") != 1
        or payload.get("producer") != PROJECT_PROFILE_PRODUCER
        or payload.get("project_dir") != str(project)
        or payload.get("source_path") != str(source)
        or not isinstance(payload.get("source_sha256"), str)
        or not re.fullmatch(r"[0-9a-f]{64}", payload["source_sha256"])
        or not isinstance(payload.get("frozen_text"), str)
        or not isinstance(payload.get("context_sha256"), str)
        or not re.fullmatch(r"[0-9a-f]{64}", payload["context_sha256"])
        or _profile_context_sha256(payload) != payload["context_sha256"]
        or hashlib.sha256(
            payload["frozen_text"].encode("utf-8")
        ).hexdigest()
        != payload["source_sha256"]
    ):
        raise VisualEvidenceError("Current project profile context is invalid")
    if (
        project not in source.parents
        or source_literal.is_symlink()
        or not source_literal.is_file()
    ):
        raise VisualEvidenceError(
            "Current project profile is missing or is not a regular project file"
        )
    if require_current and _file_sha256(source_literal) != payload["source_sha256"]:
        raise VisualEvidenceError(
            "Current project profile changed after the run snapshot was frozen"
        )
    return deepcopy(dict(payload))


def freeze_project_profile(
    *,
    project_dir: str | Path,
    run_dir: str | Path,
    output: str | Path,
) -> dict[str, Any]:
    """在任何视图动作前冻结当前项目画像，并发布运行内只读上下文。"""

    project = _absolute_path(project_dir, "Project directory")
    run = validate_project_run_dir(project, run_dir, create=False)
    context_path = validate_artifact_path(output, run, suffix=".json")
    expected_context_path = (run / PROJECT_PROFILE_CONTEXT_NAME).resolve()
    if context_path != expected_context_path:
        raise ValueError(
            f"Project profile context must be {PROJECT_PROFILE_CONTEXT_NAME}"
        )
    source_literal = project / PROJECT_PROFILE_RELATIVE
    source = source_literal.resolve()
    if (
        project not in source.parents
        or source_literal.is_symlink()
        or not source_literal.is_file()
    ):
        raise VisualEvidenceError(
            "Current project profile is missing or is not a regular project file"
        )
    try:
        frozen_bytes = source_literal.read_bytes()
        frozen_text = frozen_bytes.decode("utf-8")
    except (OSError, UnicodeError) as error:
        raise VisualEvidenceError(
            f"Cannot read current project profile as UTF-8: {error}"
        ) from error
    payload: dict[str, Any] = {
        "schema_version": 1,
        "producer": PROJECT_PROFILE_PRODUCER,
        "project_dir": str(project),
        "source_path": str(source),
        "source_sha256": hashlib.sha256(frozen_bytes).hexdigest(),
        "frozen_text": frozen_text,
    }
    payload["context_sha256"] = _profile_context_sha256(payload)
    _validate_project_profile_payload(payload, project, require_current=True)
    _publish_json_atomically(context_path, payload, run)
    return {
        "execution_status": "completed",
        "profile_status": "frozen",
        "profile_context": str(context_path),
        "source_path": str(source),
        "source_sha256": payload["source_sha256"],
        "context_sha256": payload["context_sha256"],
        "artifact_sha256": _file_sha256(context_path),
    }


def _bind_project_profile_context(
    *,
    project_dir: str | Path,
    run_dir: str | Path,
    context_path: str | Path,
) -> tuple[dict[str, Any], dict[str, str]]:
    project = _absolute_path(project_dir, "Project directory")
    run = validate_project_run_dir(project, run_dir, create=False)
    literal = Path(context_path)
    if literal.is_symlink():
        raise VisualEvidenceError(
            "Project profile context must be a regular run-local file"
        )
    context = validate_artifact_path(literal, run, suffix=".json")
    if (
        context != (run / PROJECT_PROFILE_CONTEXT_NAME).resolve()
        or not context.is_file()
    ):
        raise VisualEvidenceError(
            f"Project profile context must be {PROJECT_PROFILE_CONTEXT_NAME}"
        )
    payload = _read_json_object(context, "project profile context")
    validated = _validate_project_profile_payload(
        payload,
        project,
        require_current=True,
    )
    binding = {
        "path": str(context),
        "artifact_sha256": _file_sha256(context),
        "source_path": validated["source_path"],
        "source_sha256": validated["source_sha256"],
        "context_sha256": validated["context_sha256"],
    }
    return validated, binding


def _publish_json_atomically(metadata_path: Path, payload: Mapping[str, Any], run_dir: Path) -> None:
    """通过运行目录内的临时文件原子发布 JSON，且不覆盖已有文件。"""
    if metadata_path.exists():
        raise FileExistsError(f"Metadata artifact already exists: {metadata_path}")
    temporary = run_dir / f".{metadata_path.name}.{uuid.uuid4().hex}.tmp"
    published = False
    try:
        serialized = _serialize_json(payload)
        with temporary.open("xb") as stream:
            stream.write(serialized)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, metadata_path)
        published = True
    except OSError as error:
        raise RealMachineError(f"Cannot publish capture metadata: {error}") from error
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        except OSError as cleanup_error:
            if published:
                try:
                    metadata_path.unlink()
                except OSError as rollback_error:
                    raise RealMachineError(
                        f"Cannot remove temporary metadata: {cleanup_error}; metadata rollback failed: {rollback_error}"
                    ) from cleanup_error
            raise RealMachineError(f"Cannot remove temporary metadata: {cleanup_error}") from cleanup_error


def _rollback_capture_publication(output: Path | None, metadata: Path | None) -> None:
    """只移除本次调用已发布的产物。"""
    cleanup_errors: list[str] = []
    for artifact in (output, metadata):
        if artifact is None:
            continue
        try:
            artifact.unlink()
        except FileNotFoundError:
            pass
        except OSError as error:
            cleanup_errors.append(f"{artifact}: {error}")
    if cleanup_errors:
        raise RealMachineError(f"Cannot roll back capture publication: {'; '.join(cleanup_errors)}")


def _emit_json(payload: Mapping[str, Any]) -> None:
    print(_serialize_json(payload).decode("utf-8"))


def _emit_blocked(reason: str) -> None:
    try:
        _emit_json(
            {
                "execution_status": "blocked",
                "screening_result": "unjudgeable",
                "visual_verdict": None,
                "reason": reason,
            }
        )
    except (OSError, RealMachineError):
        pass


def _emit_unjudgeable(reason: str) -> None:
    try:
        _emit_json(
            {
                "execution_status": "completed",
                "screening_result": "unjudgeable",
                "visual_verdict": None,
                "reason": reason,
            }
        )
    except (OSError, RealMachineError):
        pass


def _default_native_discovery(**kwargs: Any) -> dict[str, Any]:
    from uia_locator import discover_canvas

    return discover_canvas(**kwargs)


def _default_wgc_capture(**kwargs: Any) -> dict[str, Any]:
    try:
        from wgc_capture import capture_window_crop

        return capture_window_crop(**kwargs)
    except UnjudgeableError:
        raise
    except Exception as error:
        raise UnjudgeableError(f"WGC capture failed: {error}") from error


def _validate_native_location(location: Any) -> dict[str, Any]:
    if not isinstance(location, Mapping):
        raise UnjudgeableError("UIA locator did not return an object")
    required = (
        "top_hwnd",
        "canvas_hwnd",
        "window_rect",
        "canvas_rect",
        "window_state_action",
        "window_restore_attempts",
    )
    missing = [field for field in required if field not in location]
    if missing:
        raise UnjudgeableError(f"UIA locator result is missing: {', '.join(missing)}")
    normalized = dict(location)
    for field in ("top_hwnd", "canvas_hwnd"):
        value = location[field]
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise UnjudgeableError(f"UIA locator returned invalid {field}")
        normalized[field] = value
    rectangles: dict[str, dict[str, int]] = {}
    for field in ("window_rect", "canvas_rect"):
        value = location[field]
        if not isinstance(value, Mapping):
            raise UnjudgeableError(f"UIA locator returned invalid {field}")
        rectangle: dict[str, int] = {}
        for coordinate in ("left", "top", "right", "bottom"):
            item = value.get(coordinate)
            if isinstance(item, bool) or not isinstance(item, int):
                raise UnjudgeableError(f"UIA locator returned invalid {field}.{coordinate}")
            rectangle[coordinate] = item
        if rectangle["right"] <= rectangle["left"] or rectangle["bottom"] <= rectangle["top"]:
            raise UnjudgeableError(f"UIA locator returned an empty {field}")
        rectangles[field] = rectangle
        normalized[field] = rectangle
    window, canvas = rectangles["window_rect"], rectangles["canvas_rect"]
    if (
        canvas["left"] < window["left"]
        or canvas["top"] < window["top"]
        or canvas["right"] > window["right"]
        or canvas["bottom"] > window["bottom"]
    ):
        raise UnjudgeableError("UIA canvas rectangle falls outside its window")
    root_hwnd = location.get("root_hwnd")
    if root_hwnd is not None:
        if isinstance(root_hwnd, bool) or not isinstance(root_hwnd, int) or root_hwnd != normalized["top_hwnd"]:
            raise UnjudgeableError("UIA root HWND does not match the top-level window")
        normalized["root_hwnd"] = root_hwnd
    window_state_action = location["window_state_action"]
    window_restore_attempts = location["window_restore_attempts"]
    if (
        not isinstance(window_state_action, str)
        or isinstance(window_restore_attempts, bool)
        or not isinstance(window_restore_attempts, int)
        or (window_state_action, window_restore_attempts)
        not in (("none", 0), ("restored-from-minimized", 1))
    ):
        raise UnjudgeableError("UIA locator returned invalid window restore metadata")
    normalized["window_state_action"] = window_state_action
    normalized["window_restore_attempts"] = window_restore_attempts
    return normalized


def capture_canvas(
    location_payload: Mapping[str, Any],
    output: str | Path,
    *,
    project_dir: str | Path,
    run_dir: str | Path,
    capture_backend: Callable[..., Mapping[str, Any]] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """依据 UIA 原生几何，通过 WGC 捕获已验证画布。"""
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ValueError("Capture timeout must be positive")
    planned_run_dir = validate_project_run_dir(project_dir, run_dir, create=False)
    output_path = validate_capture_path(output, planned_run_dir)
    verified = validate_semantic_identity(location_payload)
    validated_run_dir = validate_project_run_dir(project_dir, planned_run_dir)
    output_path = validate_capture_path(output_path, validated_run_dir)
    if output_path.exists():
        raise FileExistsError(f"Capture artifact already exists: {output_path}")
    location = _validate_native_location(location_payload)
    backend = capture_backend or _default_wgc_capture
    output_was_absent = not output_path.exists()
    try:
        raw = backend(
            output=output_path,
            run_dir=validated_run_dir,
            project_dir=_absolute_path(project_dir, "Project directory"),
            window_hwnd=location["top_hwnd"],
            canvas_hwnd=location["canvas_hwnd"],
            window_rect=location["window_rect"],
            canvas_rect=location["canvas_rect"],
            timeout=float(timeout),
        )
        if not isinstance(raw, Mapping):
            raise UnjudgeableError("WGC backend did not return metadata")
        capture_result = dict(raw)
        if capture_result.get("status") != "captured":
            raise UnjudgeableError("WGC backend did not report a captured image")
        if not output_path.is_file() or output_path.stat().st_size == 0:
            raise UnjudgeableError("WGC backend did not write an image")
        width, height = _read_png_size(output_path)
        expected_size = {
            "width": location["canvas_rect"]["right"] - location["canvas_rect"]["left"],
            "height": location["canvas_rect"]["bottom"] - location["canvas_rect"]["top"],
        }
        actual_size = {"width": width, "height": height}
        if actual_size != expected_size:
            raise UnjudgeableError(
                f"PNG dimensions do not match the verified canvas: {actual_size} != {expected_size}"
            )
        canonical_backend_fields = {
            "top_hwnd": location["top_hwnd"],
            "canvas_hwnd": location["canvas_hwnd"],
            "window_rect": location["window_rect"],
            "canvas_rect": location["canvas_rect"],
            "image_size": actual_size,
        }
        if "root_hwnd" in location:
            canonical_backend_fields["root_hwnd"] = location["root_hwnd"]
        for field, expected in canonical_backend_fields.items():
            if field in capture_result and capture_result[field] != expected:
                raise UnjudgeableError(f"WGC backend metadata conflicts with verified {field}")
        if "root_hwnd" in capture_result and "root_hwnd" not in canonical_backend_fields:
            raise UnjudgeableError("WGC backend supplied an unverified root_hwnd")
    except Exception:
        if output_was_absent and output_path.exists():
            try:
                output_path.unlink()
            except OSError as cleanup_error:
                raise UnjudgeableError(f"Failed to remove incomplete capture: {cleanup_error}") from cleanup_error
        raise
    protected_fields = {
        "source", "status", "execution_status", "identity_verified", "window_ref", "canvas_ref",
        "window", "canvas_name", "screenshot", "image_size", "capture_mode", "full_screen",
        "toolbar_included", "status_bar_included", "window_hwnd", "top_hwnd", "canvas_hwnd",
        "root_hwnd", "window_rect", "canvas_rect", "dpi_awareness", "window_rect_source",
        "canvas_rect_raw", "canvas_rect_adjustment", "capture_target", "crop_source",
        "window_state_action", "window_restore_attempts",
    }
    result: dict[str, Any] = {
        "source": verified["source"],
        "status": "captured",
        "execution_status": "completed",
        "identity_verified": True,
        "window_ref": verified["window_ref"],
        "canvas_ref": verified["canvas_ref"],
        "window": {
            "ref": verified["window_ref"],
            "title": verified["window_title"],
            "process_name": verified["process_name"],
        },
        "canvas_name": verified["canvas_name"],
        "screenshot": str(output_path),
        "image_size": {"width": width, "height": height},
        "capture_mode": "wgc-window-crop",
        "capture_target": "top-level-window",
        "crop_source": "uia-canvas-rect",
        "full_screen": False,
        "toolbar_included": False,
        "status_bar_included": False,
        "top_hwnd": location["top_hwnd"],
        "canvas_hwnd": location["canvas_hwnd"],
        "window_rect": location["window_rect"],
        "canvas_rect": location["canvas_rect"],
        "window_state_action": location["window_state_action"],
        "window_restore_attempts": location["window_restore_attempts"],
    }
    if "root_hwnd" in location:
        result["root_hwnd"] = location["root_hwnd"]
    for field in (
        "dpi_awareness",
        "window_rect_source",
        "canvas_rect_raw",
        "canvas_rect_adjustment",
    ):
        if field in location:
            result[field] = location[field]
    result.update({key: value for key, value in location.items() if key not in protected_fields})
    result.update({key: value for key, value in capture_result.items() if key not in protected_fields})
    return result


def capture_auto(
    output: str | Path,
    *,
    project_dir: str | Path,
    run_dir: str | Path,
    metadata: str | Path | None = None,
    discovery: Callable[..., Mapping[str, Any]] | None = None,
    capture_backend: Callable[..., Mapping[str, Any]] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """发现唯一原生 UIA 画布，并将同一次定位结果直接交给 WGC。"""
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ValueError("Capture timeout must be positive")
    project = _absolute_path(project_dir, "Project directory")
    planned_run = validate_project_run_dir(project, run_dir, create=False)
    output_path = validate_capture_path(output, planned_run)
    metadata_path = (
        validate_artifact_path(metadata, planned_run, suffix=".json")
        if metadata is not None
        else None
    )
    if output_path.exists():
        raise FileExistsError(f"Capture artifact already exists: {output_path}")
    if metadata_path is not None and metadata_path.exists():
        raise FileExistsError(f"Metadata artifact already exists: {metadata_path}")

    selected_discovery = discovery or _default_native_discovery
    try:
        location = selected_discovery(
            process_name=DEFAULT_PROCESS_NAME,
            canvas_name=DEFAULT_CANVAS_NAME,
            timeout=float(timeout),
        )
    except Exception as error:
        reason_code = getattr(error, "reason_code", None)
        if (
            getattr(error, "execution_status", None) == "completed"
            and getattr(error, "screening_result", None) == "unjudgeable"
            and reason_code in {
                "window_not_unique",
                "canvas_not_unique",
                "canvas_not_pane",
            }
        ):
            return {
                "execution_status": "completed",
                "status": "unjudgeable",
                "screening_result": "unjudgeable",
                "visual_verdict": None,
                "reason": str(error),
                "reason_code": reason_code,
            }
        raise RealMachineError(f"Native UIA discovery failed: {error}") from error

    try:
        validated_location = _validate_native_location(location)
        validate_semantic_identity(validated_location)
    except (TypeError, ValueError, RealMachineError) as error:
        raise RealMachineError(f"Native UIA discovery returned invalid data: {error}") from error

    return capture_canvas(
        validated_location,
        output_path,
        project_dir=project,
        run_dir=planned_run,
        capture_backend=capture_backend,
        timeout=float(timeout),
    )


def _publish_image_atomically(image: Image.Image, target: Path, run_dir: Path) -> None:
    """原子发布一张派生 PNG，且不覆盖已有产物。"""

    if target.exists():
        raise FileExistsError(f"Derived image already exists: {target}")
    temporary = run_dir / f".{target.name}.{uuid.uuid4().hex}.tmp"
    published = False
    try:
        image.save(temporary, format="PNG")
        with temporary.open("r+b") as stream:
            os.fsync(stream.fileno())
        os.link(temporary, target)
        published = True
    except (OSError, ValueError) as error:
        raise RealMachineError(f"Cannot publish derived PNG: {error}") from error
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        except OSError as cleanup_error:
            if published:
                try:
                    target.unlink()
                except OSError as rollback_error:
                    raise RealMachineError(
                        f"Cannot clean derived PNG temporary file: {cleanup_error}; "
                        f"rollback failed: {rollback_error}"
                    ) from cleanup_error
            raise RealMachineError(
                f"Cannot clean derived PNG temporary file: {cleanup_error}"
            ) from cleanup_error


def _foreground_bands(
    mask: Image.Image,
    width: int,
    height: int,
) -> list[tuple[int, tuple[int, int, int, int]]]:
    """按横向像素投影提取结构带，避免细竖线桥接工具栏与模型。"""

    pixels = mask.tobytes()
    row_counts = [
        sum(1 for value in pixels[y * width : (y + 1) * width] if value)
        for y in range(height)
    ]
    minimum_dense_pixels = max(
        16,
        int(width * PRIMARY_BAND_DENSE_ROW_RATIO),
    )
    dense_rows = [
        y for y, count in enumerate(row_counts) if count >= minimum_dense_pixels
    ]
    if not dense_rows:
        return []

    maximum_cluster_gap = max(
        2,
        int(height * PRIMARY_BAND_DENSE_CLUSTER_GAP_RATIO),
    )
    dense_groups: list[tuple[int, int]] = []
    first = previous = dense_rows[0]
    for row in dense_rows[1:]:
        if row - previous > maximum_cluster_gap:
            dense_groups.append((first, previous + 1))
            first = row
        previous = row
    dense_groups.append((first, previous + 1))

    def band_from_rows(
        top: int,
        bottom: int,
    ) -> tuple[int, tuple[int, int, int, int]] | None:
        left = width
        right = 0
        painted_pixels = 0
        for y in range(top, bottom):
            row = pixels[y * width : (y + 1) * width]
            painted_x = [x for x, value in enumerate(row) if value]
            if not painted_x:
                continue
            painted_pixels += len(painted_x)
            left = min(left, painted_x[0])
            right = max(right, painted_x[-1] + 1)
        if right > left:
            return painted_pixels, (left, top, right, bottom)
        return None

    raw_bands = [
        band
        for top, bottom in dense_groups
        if (band := band_from_rows(top, bottom)) is not None
    ]
    if not raw_bands:
        return []

    maximum_chord_gap = max(
        4,
        int(height * PRIMARY_BAND_MAX_CHORD_GAP_RATIO),
    )
    maximum_chord_height = max(
        3,
        int(height * PRIMARY_BAND_MAX_CHORD_HEIGHT_RATIO),
    )
    maximum_endpoint_delta = max(4, int(width * 0.05))

    def chords_align(
        first_band: tuple[int, tuple[int, int, int, int]],
        second_band: tuple[int, tuple[int, int, int, int]],
    ) -> bool:
        first_box = first_band[1]
        second_box = second_band[1]
        first_width = first_box[2] - first_box[0]
        second_width = second_box[2] - second_box[0]
        overlap = max(
            0,
            min(first_box[2], second_box[2])
            - max(first_box[0], second_box[0]),
        )
        first_edges = (first_box[0] == 0, first_box[2] == width)
        second_edges = (second_box[0] == 0, second_box[2] == width)
        return (
            first_box[3] - first_box[1] <= maximum_chord_height
            and second_box[3] - second_box[1] <= maximum_chord_height
            and 0 <= second_box[1] - first_box[3] <= maximum_chord_gap
            and first_width / width >= PRIMARY_BAND_MIN_WIDTH_RATIO
            and second_width / width >= PRIMARY_BAND_MIN_WIDTH_RATIO
            and overlap / min(first_width, second_width) >= 0.90
            and abs(first_box[0] - second_box[0]) <= maximum_endpoint_delta
            and abs(first_box[2] - second_box[2]) <= maximum_endpoint_delta
            and first_edges == second_edges
        )

    chord_groups: list[
        list[tuple[int, tuple[int, int, int, int]]]
    ] = [[raw_bands[0]]]
    for band in raw_bands[1:]:
        if chords_align(chord_groups[-1][-1], band):
            chord_groups[-1].append(band)
        else:
            chord_groups.append([band])

    bands: list[tuple[int, tuple[int, int, int, int]]] = []
    for group in chord_groups:
        top = group[0][1][1]
        bottom = group[-1][1][3]
        merged = band_from_rows(top, bottom)
        if merged is not None:
            bands.append(merged)
    return bands


def _largest_foreground_bbox(
    image: Image.Image,
    *,
    require_longitudinal: bool = False,
) -> tuple[int, int, int, int]:
    """返回主纵向结构带包围框，并排除工具栏、标签和孤立噪点。"""

    rgb = image.convert("RGB")
    width, height = rgb.size
    corners = (
        rgb.getpixel((0, 0)),
        rgb.getpixel((width - 1, 0)),
        rgb.getpixel((0, height - 1)),
        rgb.getpixel((width - 1, height - 1)),
    )
    background = max(set(corners), key=corners.count)
    background_image = Image.new("RGB", rgb.size, background)
    channels = ImageChops.difference(rgb, background_image).split()
    strongest = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2])
    mask = strongest.point(lambda value: 255 if value > BACKGROUND_TOLERANCE else 0)
    bands = _foreground_bands(mask, width, height)
    if not bands:
        raise VisualEvidenceError("Model foreground cannot be isolated")
    eligible: list[tuple[int, tuple[int, int, int, int]]] = []
    for painted_pixels, band in bands:
        band_width = band[2] - band[0]
        band_height = band[3] - band[1]
        center_y_ratio = ((band[1] + band[3]) / 2) / height
        if (
            not require_longitudinal
            or (
                band_height >= 3
                and band_width / width >= PRIMARY_BAND_MIN_WIDTH_RATIO
                and band_width / band_height >= PRIMARY_BAND_MIN_ASPECT_RATIO
                and PRIMARY_BAND_MIN_CENTER_Y_RATIO
                <= center_y_ratio
                <= PRIMARY_BAND_MAX_CENTER_Y_RATIO
            )
        ):
            eligible.append((painted_pixels, band))
    if not eligible:
        raise VisualEvidenceError(
            "Primary longitudinal model band cannot be isolated from canvas controls"
        )
    def band_score(
        item: tuple[int, tuple[int, int, int, int]],
    ) -> tuple[float, int, int]:
        painted_pixels, band = item
        band_width = band[2] - band[0]
        band_height = band[3] - band[1]
        center_y_ratio = ((band[1] + band[3]) / 2) / height
        center_factor = max(0.10, 1.0 - abs(center_y_ratio - 0.50))
        edge_contacts = int(band[0] == 0) + int(band[2] == width)
        edge_factor = PRIMARY_BAND_CANVAS_EDGE_FACTOR**edge_contacts
        geometric_score = (
            band_width * band_height * center_factor * edge_factor
        )
        return geometric_score, band_width, painted_pixels

    return max(eligible, key=band_score)[1]


def _box_dict(box: tuple[int, int, int, int]) -> dict[str, int]:
    left, top, right, bottom = box
    return {"left": left, "top": top, "right": right, "bottom": bottom}


def crop_capture(
    source: str | Path,
    output: str | Path,
    *,
    project_dir: str | Path,
    run_dir: str | Path,
    box: tuple[int, int, int, int] | None,
    auto_body: bool = False,
    horizontal_range: tuple[int, int] | None = None,
    metadata: str | Path | None = None,
) -> dict[str, Any]:
    """将运行目录内的 PNG 裁剪为另一张运行目录内 PNG。"""

    planned_run = validate_project_run_dir(project_dir, run_dir, create=False)
    source_path = validate_capture_path(source, planned_run)
    output_path = validate_capture_path(output, planned_run)
    metadata_path = (
        validate_artifact_path(metadata, planned_run, suffix=".json")
        if metadata is not None
        else None
    )
    if source_path == output_path:
        raise ValueError("Crop source and output must differ")
    if not source_path.is_file():
        raise FileNotFoundError(f"Crop source does not exist: {source_path}")
    if metadata_path is not None and metadata_path.exists():
        raise FileExistsError(f"Metadata artifact already exists: {metadata_path}")
    if auto_body and box is not None:
        raise ValueError("Auto body crop cannot use an explicit crop box")
    if not auto_body and box is None:
        raise ValueError("Crop box is required unless auto body crop is enabled")
    if horizontal_range is not None and not auto_body:
        raise ValueError("Horizontal range requires auto body crop")

    validated_run = validate_project_run_dir(project_dir, planned_run)
    foreground_box: tuple[int, int, int, int] | None = None
    try:
        with Image.open(source_path) as source_image:
            if source_image.format != "PNG":
                raise ValueError("Crop source must contain PNG data")
            width, height = source_image.size
            if auto_body:
                foreground_box = _largest_foreground_bbox(
                    source_image,
                    require_longitudinal=True,
                )
                foreground_left, foreground_top, foreground_right, foreground_bottom = (
                    foreground_box
                )
                if horizontal_range is None:
                    left = max(0, foreground_left - AUTO_BODY_PADDING)
                    right = min(width, foreground_right + AUTO_BODY_PADDING)
                else:
                    if (
                        len(horizontal_range) != 2
                        or any(
                            isinstance(value, bool) or not isinstance(value, int)
                            for value in horizontal_range
                        )
                    ):
                        raise ValueError("Horizontal range must contain two integers")
                    left, right = horizontal_range
                top = max(0, foreground_top - AUTO_BODY_PADDING)
                bottom = min(height, foreground_bottom + AUTO_BODY_PADDING)
            else:
                assert box is not None
                if len(box) != 4 or any(
                    isinstance(value, bool) or not isinstance(value, int) for value in box
                ):
                    raise ValueError("Crop box must contain four integers")
                left, top, right, bottom = box
            if left < 0 or top < 0 or right <= left or bottom <= top:
                raise ValueError("Crop box must have positive dimensions")
            if right > width or bottom > height:
                raise ValueError("Crop box falls outside the source image")
            cropped = source_image.crop((left, top, right, bottom)).copy()
    except OSError as error:
        raise UnjudgeableError(f"Cannot read crop source: {error}") from error

    result: dict[str, Any] = {
        "status": "cropped",
        "crop_mode": (
            "auto-body"
            if auto_body and horizontal_range is None
            else "auto-body-local"
            if auto_body
            else "explicit"
        ),
        "source": str(source_path),
        "screenshot": str(output_path),
        "source_sha256": _file_sha256(source_path),
        "crop_rect": {"left": left, "top": top, "right": right, "bottom": bottom},
        "image_size": {"width": cropped.width, "height": cropped.height},
    }
    if foreground_box is not None:
        foreground_left, foreground_top, foreground_right, foreground_bottom = foreground_box
        visible_foreground_height = min(bottom, foreground_bottom) - max(top, foreground_top)
        foreground_height_ratio = visible_foreground_height / cropped.height
        if foreground_height_ratio < MIN_FOREGROUND_HEIGHT_RATIO:
            raise VisualEvidenceError(
                "Model foreground is below 30% after tight crop"
            )
        result.update(
            {
                "coordinate_space": "evidence_local",
                "foreground_bbox_source": _box_dict(foreground_box),
                "foreground_bbox_local": _box_dict(
                    (
                        max(left, foreground_left) - left,
                        max(top, foreground_top) - top,
                        min(right, foreground_right) - left,
                        min(bottom, foreground_bottom) - top,
                    )
                ),
                "foreground_height_ratio": foreground_height_ratio,
                "crop_transform_to_capture": {"offset_x": left, "offset_y": top},
            }
        )
    _publish_image_atomically(cropped, output_path, validated_run)
    try:
        result["screenshot_sha256"] = _file_sha256(output_path)
        if metadata_path is not None:
            _publish_json_atomically(metadata_path, result, validated_run)
    except (OSError, RealMachineError, TypeError, ValueError) as error:
        try:
            _rollback_capture_publication(output_path, None)
        except RealMachineError as cleanup_error:
            raise RealMachineError(f"{error}; {cleanup_error}") from error
        raise
    return result


def _visual_input_paths(
    run_dir: Path,
    prefix: str,
) -> tuple[dict[str, Path], Path]:
    if not isinstance(prefix, str) or not VISUAL_PREFIX_PATTERN.fullmatch(prefix):
        raise ValueError(
            "Visual input prefix must start with a letter and contain only "
            "letters, digits, hyphens or underscores"
        )
    views = {
        "full": validate_capture_path(run_dir / f"{prefix}-body.png", run_dir),
        "left": validate_capture_path(run_dir / f"{prefix}-left.png", run_dir),
        "middle": validate_capture_path(run_dir / f"{prefix}-middle.png", run_dir),
        "right": validate_capture_path(run_dir / f"{prefix}-right.png", run_dir),
    }
    receipt = validate_artifact_path(
        run_dir / f"{prefix}-visual-inputs.json",
        run_dir,
        suffix=".json",
    )
    return views, receipt


def _triptych_boxes(
    body_box: tuple[int, int, int, int],
) -> dict[str, tuple[int, int, int, int]]:
    left, top, right, bottom = body_box
    width = right - left
    if width < 6:
        raise VisualEvidenceError("Model body is too narrow for three visual segments")
    first = left + width // 3
    second = left + (2 * width) // 3
    overlap = max(1, round(width * TRIPTYCH_OVERLAP_RATIO))
    return {
        "full": body_box,
        "left": (left, top, min(right, first + overlap), bottom),
        "middle": (
            max(left, first - overlap),
            top,
            min(right, second + overlap),
            bottom,
        ),
        "right": (max(left, second - overlap), top, right, bottom),
    }


def crop_visual_inputs(
    source: str | Path,
    *,
    project_dir: str | Path,
    run_dir: str | Path,
    prefix: str,
) -> dict[str, Any]:
    """生成全梁、左段、跨中段和右段四张视觉输入及一份回执。"""

    planned_run = validate_project_run_dir(project_dir, run_dir, create=False)
    source_path = validate_capture_path(source, planned_run)
    if not source_path.is_file():
        raise FileNotFoundError(f"Crop source does not exist: {source_path}")
    view_paths, receipt_path = _visual_input_paths(planned_run, prefix)
    if source_path in view_paths.values():
        raise ValueError("Visual input source and outputs must differ")
    existing = [
        path
        for path in (*view_paths.values(), receipt_path)
        if path.exists()
    ]
    if existing:
        raise FileExistsError(f"Visual input artifact already exists: {existing[0]}")

    validated_run = validate_project_run_dir(project_dir, planned_run)
    try:
        with Image.open(source_path) as source_image:
            if source_image.format != "PNG":
                raise ValueError("Crop source must contain PNG data")
            width, height = source_image.size
            foreground_box = _largest_foreground_bbox(
                source_image,
                require_longitudinal=True,
            )
            foreground_left, foreground_top, foreground_right, foreground_bottom = (
                foreground_box
            )
            body_box = (
                max(0, foreground_left - AUTO_BODY_PADDING),
                max(0, foreground_top - AUTO_BODY_PADDING),
                min(width, foreground_right + AUTO_BODY_PADDING),
                min(height, foreground_bottom + AUTO_BODY_PADDING),
            )
            body_height = body_box[3] - body_box[1]
            foreground_height_ratio = (
                foreground_bottom - foreground_top
            ) / body_height
            if foreground_height_ratio < MIN_FOREGROUND_HEIGHT_RATIO:
                raise VisualEvidenceError(
                    "Model foreground is below 30% after tight crop"
                )
            boxes = _triptych_boxes(body_box)
            images = {
                name: source_image.crop(boxes[name]).copy()
                for name in VISUAL_VIEW_ORDER
            }
    except OSError as error:
        raise UnjudgeableError(f"Cannot read crop source: {error}") from error

    published: list[Path] = []
    try:
        for name in VISUAL_VIEW_ORDER:
            _publish_image_atomically(
                images[name],
                view_paths[name],
                validated_run,
            )
            published.append(view_paths[name])

        result: dict[str, Any] = {
            "status": "cropped",
            "crop_mode": "auto-body-triptych",
            "source": str(source_path),
            "source_sha256": _file_sha256(source_path),
            "receipt": str(receipt_path),
            "view_order": list(VISUAL_VIEW_ORDER),
            "foreground_bbox_source": _box_dict(foreground_box),
            "foreground_height_ratio": foreground_height_ratio,
            "triptych_overlap_ratio": TRIPTYCH_OVERLAP_RATIO,
            "views": {},
        }
        for name in VISUAL_VIEW_ORDER:
            box = boxes[name]
            image = images[name]
            result["views"][name] = {
                "screenshot": str(view_paths[name]),
                "screenshot_sha256": _file_sha256(view_paths[name]),
                "crop_rect": _box_dict(box),
                "image_size": {
                    "width": image.width,
                    "height": image.height,
                },
                "crop_transform_to_capture": {
                    "offset_x": box[0],
                    "offset_y": box[1],
                },
            }
        _publish_json_atomically(receipt_path, result, validated_run)
        published.append(receipt_path)
        return result
    except (OSError, RealMachineError, TypeError, ValueError) as error:
        cleanup_errors: list[str] = []
        for artifact in reversed(published):
            try:
                artifact.unlink()
            except FileNotFoundError:
                pass
            except OSError as cleanup_error:
                cleanup_errors.append(f"{artifact}: {cleanup_error}")
        if cleanup_errors:
            raise RealMachineError(
                f"{error}; visual input rollback failed: "
                f"{'; '.join(cleanup_errors)}"
            ) from error
        raise


def _validate_visual_inputs_receipt(
    receipt_value: str | Path,
    run_dir: Path,
) -> tuple[Path, dict[str, Any]]:
    literal_receipt = Path(receipt_value)
    if literal_receipt.is_symlink():
        raise VisualEvidenceError(
            "Visual inputs receipt must not be a symbolic link"
        )
    try:
        receipt_path = validate_artifact_path(
            receipt_value,
            run_dir,
            suffix=".json",
        )
        receipt = _read_json_object(receipt_path, "visual inputs receipt")
    except (OSError, RealMachineError, TypeError, ValueError) as error:
        raise VisualEvidenceError(
            f"Visual inputs receipt is invalid: {error}"
        ) from error
    if (
        receipt.get("status") != "cropped"
        or receipt.get("crop_mode") != "auto-body-triptych"
        or receipt.get("view_order") != list(VISUAL_VIEW_ORDER)
    ):
        raise VisualEvidenceError("Visual inputs receipt has an invalid contract")
    receipt_suffix = "-visual-inputs.json"
    if not receipt_path.name.endswith(receipt_suffix):
        raise VisualEvidenceError("Visual inputs receipt name is invalid")
    prefix = receipt_path.name[: -len(receipt_suffix)]
    expected_view_names = {
        "full": f"{prefix}-body.png",
        "left": f"{prefix}-left.png",
        "middle": f"{prefix}-middle.png",
        "right": f"{prefix}-right.png",
    }
    try:
        source_literal = Path(receipt.get("source", ""))
        if source_literal.is_symlink():
            raise VisualEvidenceError(
                "Visual input source must not be a symbolic link"
            )
        source_path = validate_capture_path(source_literal, run_dir)
        if receipt.get("source_sha256") != _file_sha256(source_path):
            raise VisualEvidenceError("Visual input source hash mismatch")
    except (OSError, RealMachineError, TypeError, ValueError) as error:
        if isinstance(error, VisualEvidenceError):
            raise
        raise VisualEvidenceError(
            f"Visual input source is invalid: {error}"
        ) from error

    views = receipt.get("views")
    if not isinstance(views, Mapping) or set(views) != set(VISUAL_VIEW_ORDER):
        raise VisualEvidenceError("Visual inputs receipt must contain four views")
    seen: set[Path] = set()
    for name in VISUAL_VIEW_ORDER:
        item = views.get(name)
        if not isinstance(item, Mapping):
            raise VisualEvidenceError(f"Visual input view is invalid: {name}")
        try:
            screenshot_literal = Path(item.get("screenshot", ""))
            if screenshot_literal.is_symlink():
                raise VisualEvidenceError(
                    f"Visual input image must not be a symbolic link: {name}"
                )
            screenshot = validate_capture_path(
                screenshot_literal,
                run_dir,
            )
            screenshot_hash = _file_sha256(screenshot)
        except (OSError, RealMachineError, TypeError, ValueError) as error:
            raise VisualEvidenceError(
                f"Visual input image is invalid ({name}): {error}"
            ) from error
        if screenshot in seen:
            raise VisualEvidenceError("Visual input views must use distinct images")
        seen.add(screenshot)
        if screenshot.name != expected_view_names[name]:
            raise VisualEvidenceError(
                f"Visual input role does not match its image: {name}"
            )
        if item.get("screenshot_sha256") != screenshot_hash:
            raise VisualEvidenceError(
                f"Visual input image hash mismatch: {name}"
            )
    return receipt_path, receipt


def _visual_result_rejection(reason: str) -> dict[str, Any]:
    return {
        "execution_status": "completed",
        "screening_result": "unjudgeable",
        "visual_verdict": None,
        "valid": False,
        "reason": reason,
    }


def validate_visual_result(
    payload: Mapping[str, Any],
    run_dir: str | Path,
    *,
    project_dir: str | Path,
    profile_context_path: str | Path,
    visual_inputs_path: str | Path,
) -> dict[str, Any]:
    """只校验直接视觉结论的结构、画像绑定和四张输入哈希。"""

    try:
        validated_run = validate_project_run_dir(
            project_dir,
            run_dir,
            create=False,
        )
        _profile, profile_binding = _bind_project_profile_context(
            project_dir=project_dir,
            run_dir=validated_run,
            context_path=profile_context_path,
        )
        receipt_path, receipt = _validate_visual_inputs_receipt(
            visual_inputs_path,
            validated_run,
        )
    except (OSError, RealMachineError, TypeError, ValueError) as error:
        return {
            "execution_status": "blocked",
            "screening_result": "unjudgeable",
            "visual_verdict": None,
            "valid": False,
            "reason": str(error),
        }

    if not isinstance(payload, Mapping):
        return _visual_result_rejection("Visual result must be an object")
    unknown = _unknown_field(payload, VISUAL_RESULT_FIELDS, "$")
    if unknown is not None:
        return _visual_result_rejection(
            f"Visual result contains unknown field: {unknown}"
        )
    screening_result = payload.get("screening_result")
    if screening_result not in VISUAL_RESULT_VALUES:
        return _visual_result_rejection("Visual result status is invalid")
    expected_verdict = "incorrect" if screening_result == "incorrect" else None
    if payload.get("visual_verdict") != expected_verdict:
        return _visual_result_rejection(
            "visual_verdict does not match screening_result"
        )
    reviewed_views = payload.get("reviewed_views")
    if reviewed_views != list(VISUAL_VIEW_ORDER):
        return _visual_result_rejection(
            "reviewed_views must contain full, left, middle and right in order"
        )
    summary = payload.get("summary")
    if not isinstance(summary, str) or not summary.strip() or "\x00" in summary:
        return _visual_result_rejection("Visual result summary is invalid")
    issues = payload.get("issues")
    if not isinstance(issues, list):
        return _visual_result_rejection("Visual result issues must be a list")
    if screening_result == "incorrect" and not issues:
        return _visual_result_rejection(
            "incorrect requires at least one visual issue"
        )
    if screening_result != "incorrect" and issues:
        return _visual_result_rejection(
            f"{screening_result} cannot contain visual issues"
        )

    normalized_issues: list[dict[str, Any]] = []
    issue_ids: set[str] = set()
    for issue in issues:
        if not isinstance(issue, Mapping):
            return _visual_result_rejection("Visual issue must be an object")
        unknown = _unknown_field(issue, VISUAL_ISSUE_FIELDS, "$.issues[]")
        if unknown is not None:
            return _visual_result_rejection(
                f"Visual issue contains unknown field: {unknown}"
            )
        issue_id = issue.get("issue_id")
        issue_type = issue.get("issue_type")
        region = issue.get("region")
        description = issue.get("description")
        if (
            not isinstance(issue_id, str)
            or not issue_id.strip()
            or "\x00" in issue_id
            or issue_id in issue_ids
        ):
            return _visual_result_rejection("Visual issue_id is invalid")
        if (
            not isinstance(issue_type, str)
            or not issue_type.strip()
            or "\x00" in issue_type
        ):
            return _visual_result_rejection("Visual issue_type is invalid")
        if region not in VISUAL_ISSUE_REGIONS:
            return _visual_result_rejection("Visual issue region is invalid")
        if (
            not isinstance(description, str)
            or not description.strip()
            or "\x00" in description
        ):
            return _visual_result_rejection("Visual issue description is invalid")
        normalized = {
            "issue_id": issue_id,
            "issue_type": issue_type,
            "region": region,
            "description": description,
        }
        if "bbox_normalized" in issue:
            bbox = issue.get("bbox_normalized")
            if (
                not isinstance(bbox, list)
                or len(bbox) != 4
                or any(
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    for value in bbox
                )
                or not all(0.0 <= float(value) <= 1.0 for value in bbox)
                or float(bbox[2]) <= float(bbox[0])
                or float(bbox[3]) <= float(bbox[1])
            ):
                return _visual_result_rejection(
                    "Visual issue bbox_normalized is invalid"
                )
            normalized["bbox_normalized"] = [float(value) for value in bbox]
        issue_ids.add(issue_id)
        normalized_issues.append(normalized)

    return {
        "execution_status": "completed",
        "screening_result": screening_result,
        "visual_verdict": expected_verdict,
        "verdict_scope": "current_capture",
        "valid": True,
        "reviewed_views": list(VISUAL_VIEW_ORDER),
        "summary": summary.strip(),
        "issues": normalized_issues,
        "project_profile_context": profile_binding,
        "visual_inputs": {
            "path": str(receipt_path),
            "artifact_sha256": _file_sha256(receipt_path),
            "source": receipt["source"],
            "source_sha256": receipt["source_sha256"],
            "views": deepcopy(receipt["views"]),
        },
    }


def finalize_visual_result(
    payload: Mapping[str, Any],
    *,
    project_dir: str | Path,
    run_dir: str | Path,
    input_path: str | Path,
    output_path: str | Path,
    profile_context_path: str | Path,
    visual_inputs_path: str | Path,
) -> dict[str, Any]:
    """校验直接视觉结果，发布单一清单并清理已嵌入的临时 JSON。"""

    validated_run = validate_project_run_dir(project_dir, run_dir, create=False)
    input_artifact = _validate_fixed_run_json(
        input_path,
        validated_run,
        VISUAL_RESULT_INPUT_NAME,
        must_exist=True,
    )
    output_artifact = _validate_fixed_run_json(
        output_path,
        validated_run,
        VISUAL_MANIFEST_NAME,
        must_exist=False,
    )
    if output_artifact.exists():
        raise FileExistsError(f"Manifest artifact already exists: {output_artifact}")
    stored_payload = _read_json_object(input_artifact, "visual result")
    if dict(payload) != stored_payload:
        raise VisualEvidenceError(
            "Visual result payload does not match visual-result.json"
        )

    validated = validate_visual_result(
        payload,
        validated_run,
        project_dir=project_dir,
        profile_context_path=profile_context_path,
        visual_inputs_path=visual_inputs_path,
    )
    if validated.get("valid") is not True:
        return validated

    context_path = validate_artifact_path(
        profile_context_path,
        validated_run,
        suffix=".json",
    )
    receipt_path = validate_artifact_path(
        visual_inputs_path,
        validated_run,
        suffix=".json",
    )
    profile_payload = _read_json_object(context_path, "project profile context")
    receipt_payload = _read_json_object(receipt_path, "visual inputs receipt")
    audit: dict[str, Any] = {}
    optional_audit_paths: list[Path] = []
    for name, filename in (
        ("view", "view-command.json"),
        ("capture", "before-capture.json"),
    ):
        path = validated_run / filename
        if path.is_symlink():
            raise VisualEvidenceError(
                f"{filename} must not be a symbolic link"
            )
        if path.exists() and not path.is_file():
            raise VisualEvidenceError(f"{filename} must be a regular file")
        if path.is_file():
            optional_audit_paths.append(path)
            audit[name] = {
                "path": str(path),
                "artifact_sha256": _file_sha256(path),
                "payload": _read_json_object(path, filename),
            }

    manifest = deepcopy(validated)
    manifest.update(
        {
            "producer": "osis-screenshot-check/finalize-result",
            "project_profile": profile_payload,
            "visual_inputs_receipt": receipt_payload,
            "audit": audit,
            "compaction": {
                "mode": "manifest_authoritative",
                "cleanup_failure_is_non_blocking": True,
            },
        }
    )
    manifest["visual_inputs"]["artifact_sha256"] = _file_sha256(receipt_path)
    _publish_json_atomically(output_artifact, manifest, validated_run)
    try:
        saved_manifest = _read_json_object(
            output_artifact,
            VISUAL_MANIFEST_NAME,
        )
        if saved_manifest != manifest:
            raise VisualEvidenceError("Manifest readback does not match publication")
    except (OSError, RealMachineError, TypeError, ValueError) as error:
        try:
            output_artifact.unlink()
        except OSError as rollback_error:
            raise RealMachineError(
                "Cannot read back published manifest and manifest rollback "
                f"failed: {error}; {rollback_error}"
            ) from error
        raise RealMachineError(
            f"Cannot read back published manifest: {error}"
        ) from error

    cleanup_paths = [input_artifact]
    if validated["screening_result"] != "incorrect":
        cleanup_paths.extend(
            [
                context_path,
                receipt_path,
                *optional_audit_paths,
            ]
        )
    for artifact in dict.fromkeys(cleanup_paths):
        try:
            artifact.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            # 清理失败只留下已嵌入清单的冗余副本，不影响已读回验证的清单。
            pass
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Discover and capture the OSIS canvas with native UIA/WGC"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    profile = sub.add_parser("freeze-profile")
    profile.add_argument("--project-dir", required=True)
    profile.add_argument("--run-dir", required=True)
    profile.add_argument("--output", required=True)
    auto = sub.add_parser("capture-auto")
    auto.add_argument("--project-dir", required=True)
    auto.add_argument("--run-dir", required=True)
    auto.add_argument("--output", required=True)
    auto.add_argument("--metadata")
    auto.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    crop = sub.add_parser("crop")
    crop.add_argument("--project-dir", required=True)
    crop.add_argument("--run-dir", required=True)
    crop.add_argument("--source", required=True)
    crop.add_argument("--output", required=True)
    crop.add_argument("--metadata")
    crop.add_argument("--auto-body", action="store_true")
    crop.add_argument("--left", type=int)
    crop.add_argument("--top", type=int)
    crop.add_argument("--right", type=int)
    crop.add_argument("--bottom", type=int)
    crop_views = sub.add_parser("crop-views")
    crop_views.add_argument("--project-dir", required=True)
    crop_views.add_argument("--run-dir", required=True)
    crop_views.add_argument("--source", required=True)
    crop_views.add_argument("--prefix", required=True)
    final_result = sub.add_parser("finalize-result")
    final_result.add_argument("--project-dir", required=True)
    final_result.add_argument("--run-dir", required=True)
    final_result.add_argument("--input", required=True)
    final_result.add_argument("--output", required=True)
    final_result.add_argument("--profile-context", required=True)
    final_result.add_argument("--visual-inputs", required=True)
    args = parser.parse_args()

    if args.command == "freeze-profile":
        try:
            result = freeze_project_profile(
                project_dir=args.project_dir,
                run_dir=args.run_dir,
                output=args.output,
            )
            _emit_json(result)
            return 0
        except (OSError, RealMachineError, TypeError, ValueError) as error:
            _emit_blocked(str(error))
            return 2
    if args.command == "finalize-result":
        try:
            planned_run = validate_project_run_dir(
                args.project_dir, args.run_dir, create=False
            )
            input_path = _validate_fixed_run_json(
                args.input,
                planned_run,
                VISUAL_RESULT_INPUT_NAME,
                must_exist=True,
            )
            payload = _read_json_object(input_path, "visual result")
            result = finalize_visual_result(
                payload,
                project_dir=args.project_dir,
                run_dir=planned_run,
                input_path=input_path,
                output_path=args.output,
                profile_context_path=args.profile_context,
                visual_inputs_path=args.visual_inputs,
            )
            _emit_json(result)
            return 0 if result.get("valid") is True else 2
        except (OSError, RealMachineError, TypeError, ValueError) as error:
            _emit_blocked(str(error))
            return 2
    if args.command == "crop-views":
        try:
            result = crop_visual_inputs(
                args.source,
                project_dir=args.project_dir,
                run_dir=args.run_dir,
                prefix=args.prefix,
            )
            _emit_json(result)
            return 0
        except VisualEvidenceError as error:
            _emit_unjudgeable(str(error))
            return 2
        except (OSError, RealMachineError, TypeError, ValueError) as error:
            _emit_blocked(str(error))
            return 2
    if args.command == "crop":
        crop_output: Path | None = None
        crop_metadata: Path | None = None
        crop_published = False
        try:
            planned_run = validate_project_run_dir(
                args.project_dir, args.run_dir, create=False
            )
            crop_output = validate_capture_path(args.output, planned_run)
            crop_metadata = (
                validate_artifact_path(args.metadata, planned_run, suffix=".json")
                if args.metadata
                else None
            )
            coordinates = (args.left, args.top, args.right, args.bottom)
            if args.auto_body:
                if args.top is not None or args.bottom is not None:
                    raise ValueError("Auto body crop accepts only optional left and right bounds")
                if (args.left is None) != (args.right is None):
                    raise ValueError("Auto body crop requires both left and right bounds")
                explicit_box = None
                horizontal_range = (
                    (args.left, args.right) if args.left is not None else None
                )
            else:
                if any(value is None for value in coordinates):
                    raise ValueError("Explicit crop requires left, top, right and bottom")
                explicit_box = coordinates
                horizontal_range = None
            result = crop_capture(
                args.source,
                crop_output,
                project_dir=args.project_dir,
                run_dir=planned_run,
                box=explicit_box,
                auto_body=args.auto_body,
                horizontal_range=horizontal_range,
                metadata=crop_metadata,
            )
            crop_published = True
            _emit_json(result)
            return 0
        except VisualEvidenceError as error:
            if crop_published:
                try:
                    _rollback_capture_publication(crop_output, crop_metadata)
                except RealMachineError as cleanup_error:
                    _emit_blocked(f"{error}; {cleanup_error}")
                    return 2
            _emit_unjudgeable(str(error))
            return 2
        except (OSError, RealMachineError, TypeError, ValueError) as error:
            if crop_published:
                try:
                    _rollback_capture_publication(crop_output, crop_metadata)
                except RealMachineError as cleanup_error:
                    error = RealMachineError(f"{error}; {cleanup_error}")
            _emit_blocked(str(error))
            return 2
    output: Path | None = None
    metadata_path: Path | None = None
    capture_published = False
    metadata_published = False
    try:
        project = _absolute_path(args.project_dir, "Project directory")
        planned_run = validate_project_run_dir(project, args.run_dir, create=False)
        output = validate_capture_path(args.output, planned_run)
        metadata_path = (
            validate_artifact_path(args.metadata, planned_run, suffix=".json")
            if args.metadata
            else None
        )
        result = capture_auto(
            output,
            project_dir=project,
            run_dir=planned_run,
            metadata=metadata_path,
            timeout=args.timeout,
        )
        if result.get("status") == "unjudgeable":
            if metadata_path:
                validated_run = validate_project_run_dir(project, planned_run)
                _publish_json_atomically(metadata_path, result, validated_run)
                metadata_published = True
            _emit_json(result)
            return 2
        capture_published = True
        if metadata_path:
            _publish_json_atomically(metadata_path, result, planned_run)
            metadata_published = True
        _emit_json(result)
        return 0
    except (OSError, RealMachineError, TypeError, ValueError) as error:
        if capture_published:
            try:
                _rollback_capture_publication(output, metadata_path if metadata_published else None)
            except RealMachineError as cleanup_error:
                error = RealMachineError(f"{error}; {cleanup_error}")
        _emit_blocked(str(error))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
