#!/usr/bin/env python3
"""用于 OSIS 画布截图的 Windows Graphics Capture 后端。

接收原生 UIA 已验证的顶层 HWND 和 DWM/UIA 物理矩形，捕获一帧 WGC 图像、
完成裁剪并将 PNG 写入当前项目运行目录。原生依赖固定来自 OSIS 平台包；本模块
不安装、更新或下载依赖，也不回退到桌面或 GDI 截图。
"""

from __future__ import annotations

import ctypes
import importlib.util
import math
import os
import re
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Mapping

from PIL import Image


WGC_VERSION = "2.0.0"
CAPTURE_MODE = "wgc-window-crop"
_RUN_NAME = re.compile(r"^run_\d{8}_\d{6}$")
_DATA_HOME_ENV = "XDG_DATA_HOME"
_WGC_RELATIVE_DIR = Path("wgc") / "windows-capture" / WGC_VERSION


class WgcCaptureError(RuntimeError):
    """调用方必须报告为不可判断的分类 WGC 故障。"""


def _inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _platform_data_home(path: str | Path) -> Path:
    """校验规范目录 ``<OSIS>/opencode/.local/share``。"""

    candidate = Path(path)
    rendered = str(candidate).replace("/", "\\")
    if rendered.startswith(("\\\\", "\\\\?\\", "\\\\.\\")) or not candidate.is_absolute():
        raise WgcCaptureError("platform data directory must be an absolute local path")
    resolved = candidate.resolve()
    if (
        resolved.name.casefold() != "share"
        or resolved.parent.name.casefold() != ".local"
        or resolved.parent.parent.name.casefold() != "opencode"
    ):
        raise WgcCaptureError(
            "platform data directory must be <OSIS>/opencode/.local/share"
        )
    osis_root = resolved.parents[2]
    if not (osis_root / "Osis.exe").is_file():
        raise WgcCaptureError("platform data directory is not inside a verified OSIS package")
    return resolved


def resolve_platform_wgc_dir(
    *,
    environment: Mapping[str, str] | None = None,
    script_file: str | Path | None = None,
) -> Path:
    """返回固定的平台 WGC 目录，不搜索用户路径。"""

    env = os.environ if environment is None else environment
    configured = env.get(_DATA_HOME_ENV)
    if configured and configured.strip():
        data_home = _platform_data_home(configured)
    else:
        source = Path(script_file or __file__).resolve()
        data_home = None
        for parent in source.parents:
            if (
                parent.name.casefold() == "opencode"
                and (parent.parent / "Osis.exe").is_file()
            ):
                data_home = _platform_data_home(parent / ".local" / "share")
                break
        if data_home is None:
            raise WgcCaptureError("cannot locate the WGC package inside the OSIS platform")
    install_dir = (data_home / _WGC_RELATIVE_DIR).resolve()
    if not install_dir.is_dir():
        raise WgcCaptureError(f"platform WGC package is missing: {install_dir}")
    return install_dir


def resolve_native_extension(install_dir: str | Path) -> Path:
    """返回 ``install_dir`` 下唯一的平台 ``windows_capture*.pyd``。"""

    root_input = Path(install_dir)
    if not root_input.is_absolute():
        raise WgcCaptureError("platform WGC directory must be absolute")
    try:
        root = root_input.resolve(strict=True)
    except OSError as error:
        raise WgcCaptureError(
            f"platform WGC directory is missing: {root_input}"
        ) from error
    if not root.is_dir():
        raise WgcCaptureError(f"platform WGC directory is not a directory: {root}")

    eligible: list[Path] = []
    escaped: list[Path] = []
    try:
        discovered = sorted(root.rglob("windows_capture*.pyd"))
    except OSError as error:
        raise WgcCaptureError(
            f"cannot inspect platform WGC directory: {error}"
        ) from error
    for candidate in discovered:
        try:
            resolved = candidate.resolve(strict=True)
        except OSError as error:
            raise WgcCaptureError(
                f"cannot resolve native extension candidate: {candidate}"
            ) from error
        if not _inside(resolved, root):
            escaped.append(resolved)
            continue
        if candidate.is_file():
            eligible.append(resolved)

    if escaped:
        raise WgcCaptureError(
            "native extension candidate escapes the portable install boundary"
        )
    unique = sorted(set(eligible))
    if not unique:
        raise WgcCaptureError(
            f"missing platform windows_capture extension under: {root}"
        )
    if len(unique) != 1:
        raise WgcCaptureError(
            f"platform native extension must be unique; found: {len(unique)}"
        )
    return unique[0]


def _direct_extension_loader(module_name: str, native_path: Path) -> Any:
    """直接加载扩展文件，不导入其软件包 ``__init__``。"""

    spec = importlib.util.spec_from_file_location(module_name, native_path)
    if spec is None or spec.loader is None:
        raise WgcCaptureError(f"cannot construct native module spec: {native_path}")
    native_module = importlib.util.module_from_spec(spec)
    previous = sys.modules.get(module_name)
    sys.modules[module_name] = native_module
    try:
        spec.loader.exec_module(native_module)
    except Exception as error:
        if previous is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = previous
        raise WgcCaptureError(f"cannot load platform native extension: {error}") from error
    return native_module


def load_native_extension(
    install_dir: str | Path,
    *,
    loader: Callable[[str, Path], Any] | None = None,
) -> Any:
    """直接加载唯一的平台原生扩展。

    ``loader`` 可注入，因此单元测试不需要 WGC 或真实 ``.pyd``。本函数不修改
    ``sys.path``，也不导入会连带加载 cv2/numpy 的 wheel 顶层软件包。
    """

    native_path = resolve_native_extension(install_dir)
    load = loader or _direct_extension_loader
    try:
        native_module = load("windows_capture", native_path)
    except WgcCaptureError:
        raise
    except Exception as error:
        raise WgcCaptureError(f"cannot load platform native extension: {error}") from error
    if loader is None and not hasattr(native_module, "NativeWindowsCapture"):
        raise WgcCaptureError("platform native extension lacks NativeWindowsCapture")
    return native_module


def _default_install_dir() -> Path:
    return resolve_platform_wgc_dir()


def _native_factory_from_install(install_dir: str | Path | None) -> Callable[..., Any]:
    native_module = load_native_extension(install_dir or _default_install_dir())
    factory = getattr(native_module, "NativeWindowsCapture", None)
    if not callable(factory):
        raise WgcCaptureError("platform native extension lacks a callable NativeWindowsCapture")
    return factory


def verify_platform_backend() -> dict[str, str]:
    """加载固定原生依赖，但不启动捕获。"""

    directory = _default_install_dir()
    _native_factory_from_install(directory)
    return {"wgc_version": WGC_VERSION, "wgc_directory": str(directory)}


def _rect(value: Mapping[str, Any], label: str) -> dict[str, int]:
    if not isinstance(value, Mapping):
        raise WgcCaptureError(f"{label} rect must be a mapping")
    result: dict[str, int] = {}
    for key in ("left", "top", "right", "bottom"):
        coordinate = value.get(key)
        if isinstance(coordinate, bool) or not isinstance(coordinate, int):
            raise WgcCaptureError(f"{label} rect coordinate {key} must be an integer")
        result[key] = coordinate
    if result["right"] <= result["left"] or result["bottom"] <= result["top"]:
        raise WgcCaptureError(f"{label} rect has non-positive dimensions")
    return result


def _validated_geometry(
    window_hwnd: Any,
    window_rect: Mapping[str, Any],
    canvas_rect: Mapping[str, Any],
) -> tuple[int, dict[str, int], dict[str, int]]:
    if isinstance(window_hwnd, bool) or not isinstance(window_hwnd, int) or window_hwnd <= 0:
        raise WgcCaptureError("HWND must be a positive integer")
    window = _rect(window_rect, "window")
    canvas = _rect(canvas_rect, "canvas")
    if (
        canvas["left"] < window["left"]
        or canvas["top"] < window["top"]
        or canvas["right"] > window["right"]
        or canvas["bottom"] > window["bottom"]
    ):
        raise WgcCaptureError("canvas rect is outside the DWM window rect")
    return window_hwnd, window, canvas


def _absolute(path: str | Path, label: str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        raise WgcCaptureError(f"{label} must be an absolute path")
    try:
        return candidate.resolve(strict=False)
    except OSError as error:
        raise WgcCaptureError(f"cannot resolve {label}: {error}") from error


def _validated_output(
    project_dir: str | Path,
    run_dir: str | Path,
    output: str | Path,
) -> tuple[Path, Path, Path]:
    project = _absolute(project_dir, "project directory")
    run = _absolute(run_dir, "run directory")
    target = _absolute(output, "output path")
    if not project.is_dir():
        raise WgcCaptureError(f"project directory does not exist: {project}")
    if not run.is_dir():
        raise WgcCaptureError(f"run directory does not exist: {run}")
    expected_run_root = (project / "runs" / "osis-screenshot-check").resolve(
        strict=False
    )
    if run.parent != expected_run_root or not _RUN_NAME.fullmatch(run.name):
        raise WgcCaptureError(
            "run directory must be project/runs/osis-screenshot-check/run_YYYYMMDD_HHMMSS"
        )
    if not _inside(run, project):
        raise WgcCaptureError("run directory escapes the active project boundary")
    if not _inside(target, run) or target == run:
        raise WgcCaptureError("output path must stay inside the project run directory")
    if target.suffix.lower() != ".png":
        raise WgcCaptureError("output target must be a PNG file")
    if not target.parent.is_dir():
        raise WgcCaptureError("output parent directory does not exist inside the run")
    if target.exists():
        raise WgcCaptureError("output target already exists; overwrite is forbidden")
    return project, run, target


def _stop_native(native: Any) -> None:
    stop = getattr(native, "stop", None)
    close = getattr(native, "close", None)
    errors: list[Exception] = []
    if callable(stop):
        try:
            stop()
            return
        except Exception as error:
            errors.append(error)
    if callable(close):
        try:
            close()
            return
        except Exception as error:
            errors.append(error)
    if errors:
        raise WgcCaptureError(f"cannot stop native WGC capture: {errors[-1]}") from errors[-1]
    raise WgcCaptureError("native WGC capture has no callable stop or close method")


def _wait_control(control: Any, timeout: float, *, context: str) -> None:
    """等待自由线程原生会话，并限制最长阻塞时间。

    ``windows-capture`` 的 ``wait()`` 没有超时参数，因此在短生命周期守护线程中
    调用。调用方超时时已请求 ``stop()``；等待线程仍不结束即属于捕获硬故障。
    """

    wait = getattr(control, "wait", None)
    if not callable(wait):
        raise WgcCaptureError(f"{context}: native control has no wait method")
    finished = threading.Event()
    wait_errors: list[BaseException] = []

    def run_wait() -> None:
        try:
            wait()
        except BaseException as error:  # 原生/Python 边界可能抛出 BaseException
            wait_errors.append(error)
        finally:
            finished.set()

    waiter = threading.Thread(
        target=run_wait,
        name="osis-wgc-control-wait",
        daemon=True,
    )
    waiter.start()
    wait_window = max(0.05, min(float(timeout), 1.0))
    if not finished.wait(wait_window):
        stop = getattr(control, "stop", None)
        stop_error: BaseException | None = None
        if callable(stop):
            try:
                stop()
            except BaseException as error:
                stop_error = error
        if not finished.wait(0.25):
            detail = f"{context}: native control wait timed out"
            if stop_error is not None:
                detail += f"; stop failed: {stop_error}"
            raise WgcCaptureError(detail)
    if wait_errors:
        error = wait_errors[0]
        stop = getattr(control, "stop", None)
        if callable(stop):
            try:
                stop()
            except BaseException:
                pass
        raise WgcCaptureError(f"{context}: native control wait failed: {error}") from error


def _start_free_threaded(native: Any, timeout: float) -> Any:
    """调用 ``start_free_threaded``，并限制初始化等待时间。"""

    start = getattr(native, "start_free_threaded", None)
    if not callable(start):
        raise WgcCaptureError("native WGC capture has no start_free_threaded method")
    finished = threading.Event()
    result: list[Any] = []
    errors: list[BaseException] = []

    def run_start() -> None:
        try:
            result.append(start())
        except BaseException as error:
            errors.append(error)
        finally:
            finished.set()

    starter = threading.Thread(
        target=run_start,
        name="osis-wgc-free-threaded-start",
        daemon=True,
    )
    starter.start()
    if timeout <= 0 or not finished.wait(float(timeout)):
        stop_error: BaseException | None = None
        try:
            _stop_native(native)
        except BaseException as error:
            stop_error = error
        starter.join(timeout=0.25)
        detail = f"native WGC free-threaded start timed out after {timeout:.3f}s"
        if stop_error is not None:
            detail += f"; native stop failed: {stop_error}"
        if starter.is_alive():
            detail += "; native start worker did not stop"
        raise WgcCaptureError(detail)
    if errors:
        error = errors[0]
        raise WgcCaptureError(f"native WGC free-threaded start failed: {error}") from error
    return result[0] if result else None


def _frame_image(
    *,
    pointer: Any,
    buffer_len: Any,
    width: Any,
    height: Any,
    window: Mapping[str, int],
    canvas: Mapping[str, int],
) -> Image.Image:
    if (
        isinstance(width, bool)
        or isinstance(height, bool)
        or not isinstance(width, int)
        or not isinstance(height, int)
        or width <= 0
        or height <= 0
    ):
        raise WgcCaptureError("WGC frame size is empty or invalid")
    expected_width = window["right"] - window["left"]
    expected_height = window["bottom"] - window["top"]
    if width != expected_width or height != expected_height:
        raise WgcCaptureError(
            "WGC frame size does not match the DWM window dimensions"
        )
    if (
        isinstance(buffer_len, bool)
        or not isinstance(buffer_len, int)
        or buffer_len <= 0
        or buffer_len % height != 0
    ):
        raise WgcCaptureError("WGC buffer length cannot define a valid row stride")
    row_pitch = buffer_len // height
    if row_pitch < width * 4:
        raise WgcCaptureError("WGC buffer row stride is shorter than BGRA pixels")
    try:
        address = int(pointer)
    except (TypeError, ValueError, OverflowError) as error:
        raise WgcCaptureError("WGC buffer pointer is invalid") from error
    if address <= 0:
        raise WgcCaptureError("WGC buffer pointer is null")
    try:
        raw = ctypes.string_at(address, buffer_len)
        frame = Image.frombytes(
            "RGBA",
            (width, height),
            raw,
            "raw",
            "BGRA",
            row_pitch,
            1,
        )
    except Exception as error:
        raise WgcCaptureError(f"cannot decode WGC BGRA buffer: {error}") from error

    crop = (
        canvas["left"] - window["left"],
        canvas["top"] - window["top"],
        canvas["right"] - window["left"],
        canvas["bottom"] - window["top"],
    )
    if (
        crop[0] < 0
        or crop[1] < 0
        or crop[2] > width
        or crop[3] > height
        or crop[2] <= crop[0]
        or crop[3] <= crop[1]
    ):
        raise WgcCaptureError("canvas crop is outside the WGC frame")
    return frame.crop(crop)


def _capture_first_frame(
    factory: Callable[..., Any],
    *,
    window_hwnd: int,
    window: Mapping[str, int],
    canvas: Mapping[str, int],
    timeout: float,
) -> Image.Image:
    deadline = time.monotonic() + timeout

    def remaining() -> float:
        return max(0.0, deadline - time.monotonic())

    completed = threading.Event()
    state_lock = threading.Lock()
    state: dict[str, Any] = {"image": None, "error": None, "received": False}

    def finish_with_error(error: Exception) -> None:
        with state_lock:
            if state["image"] is None and state["error"] is None:
                state["error"] = error
        completed.set()

    def on_frame(
        pointer: Any,
        buffer_len: Any,
        width: Any,
        height: Any,
        stop_list: Any,
        _timestamp: Any,
    ) -> None:
        try:
            stop_list[0] = True
        except Exception as error:
            finish_with_error(
                WgcCaptureError(f"native WGC callback cannot request first-frame stop: {error}")
            )
            return
        with state_lock:
            if state["received"]:
                return
            state["received"] = True
        try:
            image = _frame_image(
                pointer=pointer,
                buffer_len=buffer_len,
                width=width,
                height=height,
                window=window,
                canvas=canvas,
            )
        except Exception as error:
            finish_with_error(
                error
                if isinstance(error, WgcCaptureError)
                else WgcCaptureError(f"WGC frame callback failed: {error}")
            )
            return
        with state_lock:
            state["image"] = image
        completed.set()

    def on_closed(*_args: Any, **_kwargs: Any) -> None:
        with state_lock:
            has_frame = state["image"] is not None
        if not has_frame:
            finish_with_error(WgcCaptureError("native WGC capture closed before a frame arrived"))

    try:
        native = factory(
            on_frame,
            on_closed,
            cursor_capture=False,
            draw_border=False,
            window_hwnd=window_hwnd,
        )
    except Exception as error:
        raise WgcCaptureError(f"cannot create native WGC capture: {error}") from error
    # windows-capture 的自由线程接口会返回控制对象；可用时借此在超时后可靠停止
    # 原生会话。注入式测试替身和旧兼容版本继续使用阻塞式 ``start`` 路径。
    free_start = getattr(native, "start_free_threaded", None)
    if callable(free_start):
        control = _start_free_threaded(native, remaining())
        if control is None:
            raise WgcCaptureError("native WGC free-threaded start returned no control")
        if not completed.wait(remaining()):
            stop = getattr(control, "stop", None)
            if not callable(stop):
                raise WgcCaptureError(
                    f"WGC capture timeout after {timeout:.3f}s and control has no stop"
                )
            try:
                stop()
            except Exception as error:
                raise WgcCaptureError(
                    f"WGC capture timeout and native stop failed: {error}"
                ) from error
            try:
                _wait_control(control, remaining(), context="WGC capture timeout")
            except WgcCaptureError as wait_error:
                raise WgcCaptureError(
                    f"WGC capture timeout after {timeout:.3f}s; {wait_error}"
                ) from wait_error
            raise WgcCaptureError(f"WGC capture timeout after {timeout:.3f}s")
        with state_lock:
            image = state["image"]
            error = state["error"]
        try:
            _wait_control(control, remaining(), context="WGC capture")
        except WgcCaptureError as wait_error:
            if error is None:
                error = wait_error
    else:
        start = getattr(native, "start", None)
        if not callable(start):
            raise WgcCaptureError(
                "native WGC capture has neither start_free_threaded nor start"
            )

        def run_native() -> None:
            try:
                start()
            except Exception as error:
                finish_with_error(WgcCaptureError(f"native WGC capture failed: {error}"))
                return
            with state_lock:
                has_result = state["image"] is not None or state["error"] is not None
            if not has_result:
                finish_with_error(WgcCaptureError("native WGC capture returned an empty frame"))

        worker = threading.Thread(
            target=run_native,
            name="osis-wgc-first-frame",
            daemon=True,
        )
        worker.start()
        if not completed.wait(remaining()):
            try:
                _stop_native(native)
            except WgcCaptureError:
                pass
            worker.join(timeout=min(max(timeout, 0.05), 0.25))
            raise WgcCaptureError(f"WGC capture timeout after {timeout:.3f}s")

        with state_lock:
            image = state["image"]
            error = state["error"]
        try:
            if worker.is_alive():
                _stop_native(native)
            worker.join(timeout=min(max(timeout, 0.05), 0.25))
        except WgcCaptureError as stop_error:
            if error is None and image is None:
                error = stop_error
    if error is not None:
        if isinstance(error, WgcCaptureError):
            raise error
        raise WgcCaptureError(str(error)) from error
    if not isinstance(image, Image.Image):
        raise WgcCaptureError("native WGC capture produced no usable image")
    return image


def _publish_png(image: Image.Image, target: Path, run: Path) -> None:
    temporary = run / f".{target.name}.{uuid.uuid4().hex}.tmp"
    published = False
    primary_error: Exception | None = None
    cleanup_error: Exception | None = None
    try:
        image.save(temporary, format="PNG")
        with Image.open(temporary) as check:
            check.verify()
        if target.exists():
            raise FileExistsError("output target already exists; overwrite is forbidden")
        os.link(temporary, target)
        published = True
    except Exception as error:
        primary_error = error
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        except Exception as error:
            cleanup_error = error
    if primary_error is not None:
        if published:
            try:
                target.unlink()
            except Exception as rollback_error:
                raise WgcCaptureError(
                    f"PNG publish failed and rollback failed: {primary_error}; {rollback_error}"
                ) from primary_error
        detail = f"cannot atomically publish PNG: {primary_error}"
        if cleanup_error is not None:
            detail += f"; cleanup failed: {cleanup_error}"
        raise WgcCaptureError(detail) from primary_error
    if cleanup_error is not None:
        if published:
            try:
                target.unlink()
            except Exception as rollback_error:
                raise WgcCaptureError(
                    "temporary PNG cleanup failed: "
                    f"{cleanup_error}; rollback failed: {rollback_error}"
                ) from cleanup_error
        raise WgcCaptureError(f"temporary PNG cleanup failed: {cleanup_error}") from cleanup_error


def capture_window_crop(
    *,
    window_hwnd: int,
    canvas_hwnd: int | None = None,
    window_rect: Mapping[str, Any],
    canvas_rect: Mapping[str, Any],
    project_dir: str | Path,
    run_dir: str | Path,
    output: str | Path,
    timeout: float = 10.0,
    install_dir: str | Path | None = None,
    native_factory: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """捕获第一帧 WGC 图像，裁剪到画布后原子发布。"""

    if os.name != "nt":
        raise WgcCaptureError("Windows Graphics Capture requires a Windows desktop")
    if canvas_hwnd is not None and (
        isinstance(canvas_hwnd, bool)
        or not isinstance(canvas_hwnd, int)
        or canvas_hwnd <= 0
    ):
        raise WgcCaptureError("canvas HWND must be a positive integer when supplied")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        raise WgcCaptureError("capture timeout must be a positive number")
    timeout_value = float(timeout)
    if timeout_value <= 0 or not math.isfinite(timeout_value):
        raise WgcCaptureError("capture timeout must be a finite positive number")
    hwnd, window, canvas = _validated_geometry(
        window_hwnd,
        window_rect,
        canvas_rect,
    )
    _project, run, target = _validated_output(project_dir, run_dir, output)
    factory = native_factory or _native_factory_from_install(install_dir)
    image = _capture_first_frame(
        factory,
        window_hwnd=hwnd,
        window=window,
        canvas=canvas,
        timeout=timeout_value,
    )
    expected_size = (
        canvas["right"] - canvas["left"],
        canvas["bottom"] - canvas["top"],
    )
    if image.size != expected_size:
        raise WgcCaptureError(
            "cropped WGC image size does not match the physical canvas rect"
        )
    _publish_png(image, target, run)
    return {
        "status": "captured",
        "screenshot": str(target),
        "image_size": {"width": image.width, "height": image.height},
        "capture_mode": CAPTURE_MODE,
        "full_screen": False,
        "toolbar_included": False,
        "status_bar_included": False,
        "window_hwnd": hwnd,
        "canvas_hwnd": canvas_hwnd,
        "window_rect": dict(window),
        "canvas_rect": dict(canvas),
        "wgc_version": WGC_VERSION,
    }


__all__ = [
    "CAPTURE_MODE",
    "WGC_VERSION",
    "WgcCaptureError",
    "capture_window_crop",
    "load_native_extension",
    "resolve_native_extension",
]
