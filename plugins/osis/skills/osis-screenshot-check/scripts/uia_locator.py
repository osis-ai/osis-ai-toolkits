"""发现 OSIS 模型画布并返回 WGC 所需的原生身份与物理矩形。"""

from __future__ import annotations

import base64
import json
import math
import subprocess
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any


DEFAULT_TIMEOUT = 30.0
GEOMETRY_ATTEMPTS = 3
GEOMETRY_RETRY_DELAY = 0.2
RECT_FIELDS = ("left", "top", "right", "bottom")
SEMANTIC_REASON_CODES = {
    "window_not_unique",
    "canvas_not_unique",
    "canvas_not_pane",
}


class UiaLocatorError(RuntimeError):
    """无法安全证明原生 UIA 身份或几何。"""

    execution_status = "blocked"
    screening_result = "unjudgeable"
    visual_verdict = None

    def __init__(self, message: str, *, reason_code: str, retryable: bool = False):
        super().__init__(message)
        self.reason_code = reason_code
        self.retryable = retryable


class UiaIdentityError(UiaLocatorError):
    """OSIS 窗口或模型画布缺失、歧义，无法形成可判定截图。"""

    execution_status = "completed"
    screening_result = "unjudgeable"
    visual_verdict = None


def _powershell_literal(value: str) -> str:
    """生成可防止注入的 PowerShell 单引号字符串字面量。"""

    return "'" + value.replace("'", "''") + "'"


def _build_bridge_script(
    *, window_title: str | None, process_name: str, canvas_name: str
) -> str:
    title_literal = "$null" if window_title is None else _powershell_literal(window_title)
    process_literal = _powershell_literal(process_name.removesuffix(".exe"))
    canvas_literal = _powershell_literal(canvas_name)
    return rf"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$windowTitle = {title_literal}
$processName = {process_literal}
$canvasName = {canvas_literal}
# 语义画布标识按契约不区分大小写：3d绘图。
# UIA 语义类型为 ControlType.Pane；下方原生表达式使用完整的
# PowerShell ``ControlType]::Pane`` 写法。

function Emit-Blocked([string]$reasonCode, [string]$message) {{
    [ordered]@{{
        status = 'blocked'
        reason_code = $reasonCode
        message = $message
    }} | ConvertTo-Json -Compress
    exit 0
}}

try {{
    $null = Add-Type -AssemblyName UIAutomationClient
    $null = Add-Type -AssemblyName UIAutomationTypes
    $null = Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

public static class OsisUiaNative
{{
    public const uint GA_ROOT = 2;
    public const int DWMWA_EXTENDED_FRAME_BOUNDS = 9;
    public const int SW_SHOWNOACTIVATE = 4;

    [StructLayout(LayoutKind.Sequential)]
    public struct RECT
    {{
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }}

    [DllImport("user32.dll")]
    public static extern IntPtr SetThreadDpiAwarenessContext(IntPtr dpiContext);

    [DllImport("user32.dll")]
    public static extern IntPtr GetAncestor(IntPtr hwnd, uint flags);

    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool IsIconic(IntPtr hwnd);

    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool ShowWindowAsync(IntPtr hwnd, int command);

    [DllImport("user32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool GetWindowRect(IntPtr hwnd, out RECT rect);

    [DllImport("dwmapi.dll")]
    public static extern int DwmGetWindowAttribute(
        IntPtr hwnd,
        int attribute,
        out RECT value,
        int valueSize
    );
}}
'@

    # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 是文档规定的伪句柄 -4。
    # 下方所有 HWND 和矩形读取都在切换后执行。
    $DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = [IntPtr](-4)
    $previousDpiContext = [OsisUiaNative]::SetThreadDpiAwarenessContext(
        $DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
    )
    if ($previousDpiContext -eq [IntPtr]::Zero) {{
        Emit-Blocked 'dpi_context_failed' 'Unable to enter Per-Monitor V2 DPI context'
    }}

    $root = [System.Windows.Automation.AutomationElement]::RootElement
    $windowCondition = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
        [System.Windows.Automation.ControlType]::Window
    )
    $topWindows = $root.FindAll(
        [System.Windows.Automation.TreeScope]::Children,
        $windowCondition
    )
    $matchingWindows = @(
        foreach ($candidate in $topWindows) {{
            $candidatePid = [int]$candidate.GetCurrentPropertyValue(
                [System.Windows.Automation.AutomationElement]::ProcessIdProperty
            )
            try {{
                $candidateProcess = [System.Diagnostics.Process]::GetProcessById($candidatePid)
                if ($candidateProcess.ProcessName -ieq $processName) {{
                    $candidateTitle = [string]$candidate.GetCurrentPropertyValue(
                        [System.Windows.Automation.AutomationElement]::NameProperty
                    )
                    if ($null -eq $windowTitle -or $candidateTitle -ceq $windowTitle) {{
                        $candidate
                    }}
                }}
            }} catch {{
                # 进程可能在 UIA 查询与属性读取之间退出。
            }}
        }}
    )
    if ($matchingWindows.Count -ne 1) {{
        Emit-Blocked 'window_not_unique' 'Expected exactly one OSIS window'
    }}
    $window = $matchingWindows[0]
    $resolvedWindowTitle = [string]$window.GetCurrentPropertyValue(
        [System.Windows.Automation.AutomationElement]::NameProperty
    )
    if ([string]::IsNullOrWhiteSpace($resolvedWindowTitle)) {{
        Emit-Blocked 'window_title_empty' 'The OSIS window title is empty'
    }}

    $namedCanvasCondition = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::NameProperty,
        $canvasName
    )
    $namedCanvases = $window.FindAll(
        [System.Windows.Automation.TreeScope]::Descendants,
        $namedCanvasCondition
    )
    if ($namedCanvases.Count -eq 0) {{
        Emit-Blocked 'canvas_not_unique' 'No canvas with the confirmed name was found'
    }}

    $paneCondition = New-Object System.Windows.Automation.AndCondition(
        $namedCanvasCondition,
        (New-Object System.Windows.Automation.PropertyCondition(
            [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
            [System.Windows.Automation.ControlType]::Pane
        ))
    )
    $paneCanvases = $window.FindAll(
        [System.Windows.Automation.TreeScope]::Descendants,
        $paneCondition
    )
    if ($paneCanvases.Count -eq 0 -and $namedCanvases.Count -gt 0) {{
        Emit-Blocked 'canvas_not_pane' 'The confirmed canvas is not a Pane'
    }}
    if ($paneCanvases.Count -ne 1) {{
        Emit-Blocked 'canvas_not_unique' 'Expected exactly one Pane canvas'
    }}
    $canvas = $paneCanvases[0]

    $topHwnd = [IntPtr][long]$window.GetCurrentPropertyValue(
        [System.Windows.Automation.AutomationElement]::NativeWindowHandleProperty
    )
    $canvasHwnd = [IntPtr][long]$canvas.GetCurrentPropertyValue(
        [System.Windows.Automation.AutomationElement]::NativeWindowHandleProperty
    )
    if ($topHwnd -eq [IntPtr]::Zero -or $canvasHwnd -eq [IntPtr]::Zero) {{
        Emit-Blocked 'invalid_native_handle' 'A required UIA native HWND is zero'
    }}

    $GA_ROOT = [OsisUiaNative]::GA_ROOT
    $rootHwnd = [OsisUiaNative]::GetAncestor($canvasHwnd, $GA_ROOT)
    if ($rootHwnd -eq [IntPtr]::Zero -or $rootHwnd -ne $topHwnd) {{
        Emit-Blocked 'root_hwnd_mismatch' 'Canvas HWND does not belong to the OSIS root HWND'
    }}

    $windowStateAction = 'none'
    $windowRestoreAttempts = 0
    if ([OsisUiaNative]::IsIconic($topHwnd)) {{
        $windowStateAction = 'restored-from-minimized'
        $windowRestoreAttempts = 1
        $null = [OsisUiaNative]::ShowWindowAsync(
            $topHwnd,
            [OsisUiaNative]::SW_SHOWNOACTIVATE
        )

        $restorePollLimit = 20
        $windowRestored = $false
        for ($restorePoll = 0; $restorePoll -lt $restorePollLimit; $restorePoll++) {{
            Start-Sleep -Milliseconds 50
            if (-not [OsisUiaNative]::IsIconic($topHwnd)) {{
                $windowRestored = $true
                break
            }}
        }}
        if (-not $windowRestored) {{
            Emit-Blocked 'window_restore_failed' 'The proved OSIS window remained minimized'
        }}
    }}

    if ([bool]$canvas.Current.IsOffscreen) {{
        Emit-Blocked 'canvas_offscreen' 'The confirmed canvas is offscreen'
    }}

    $windowRect = New-Object OsisUiaNative+RECT
    $DWMWA_EXTENDED_FRAME_BOUNDS = [OsisUiaNative]::DWMWA_EXTENDED_FRAME_BOUNDS
    $dwmResult = [OsisUiaNative]::DwmGetWindowAttribute(
        $topHwnd,
        $DWMWA_EXTENDED_FRAME_BOUNDS,
        [ref]$windowRect,
        [System.Runtime.InteropServices.Marshal]::SizeOf(
            [type][OsisUiaNative+RECT]
        )
    )
    if ($dwmResult -ne 0) {{
        Emit-Blocked 'dwm_bounds_failed' 'Unable to read DWM extended frame bounds'
    }}

    $canvasRect = New-Object OsisUiaNative+RECT
    if (-not [OsisUiaNative]::GetWindowRect($canvasHwnd, [ref]$canvasRect)) {{
        Emit-Blocked 'canvas_bounds_failed' 'Unable to read the native canvas rectangle'
    }}

    [ordered]@{{
        status = 'located'
        window_title = $resolvedWindowTitle
        process_name = $processName
        canvas_name = $canvasName
        control_type = 'Pane'
        dpi_awareness = 'per-monitor-v2'
        window_state_action = $windowStateAction
        window_restore_attempts = $windowRestoreAttempts
        top_hwnd = [long]$topHwnd
        canvas_hwnd = [long]$canvasHwnd
        root_hwnd = [long]$rootHwnd
        window_rect_source = 'DWMWA_EXTENDED_FRAME_BOUNDS'
        window_rect = [ordered]@{{
            left = [int]$windowRect.Left
            top = [int]$windowRect.Top
            right = [int]$windowRect.Right
            bottom = [int]$windowRect.Bottom
        }}
        canvas_rect = [ordered]@{{
            left = [int]$canvasRect.Left
            top = [int]$canvasRect.Top
            right = [int]$canvasRect.Right
            bottom = [int]$canvasRect.Bottom
        }}
    }} | ConvertTo-Json -Depth 4 -Compress
}} catch {{
    [ordered]@{{
        status = 'blocked'
        reason_code = 'powershell_failed'
        message = $_.Exception.Message
    }} | ConvertTo-Json -Compress
    exit 1
}}
""".strip()


def _blocked(
    message: str, reason_code: str, *, retryable: bool = False
) -> UiaLocatorError:
    return UiaLocatorError(
        message, reason_code=reason_code, retryable=retryable
    )


def _identity_error(message: str, reason_code: str) -> UiaIdentityError:
    return UiaIdentityError(message, reason_code=reason_code)


def _parse_payload(stdout: Any) -> dict[str, Any]:
    if not isinstance(stdout, str):
        raise _blocked("UIA bridge did not return UTF-8 text JSON", "invalid_json")
    serialized = stdout.strip().lstrip("\ufeff")
    if not serialized:
        raise _blocked("UIA bridge returned empty output", "invalid_json")
    try:
        payload = json.loads(serialized)
    except (json.JSONDecodeError, TypeError) as error:
        raise _blocked(f"UIA bridge returned invalid JSON: {error}", "invalid_json") from error
    if not isinstance(payload, dict):
        raise _blocked("UIA bridge JSON root must be an object", "invalid_json")
    return payload


def _positive_handle(payload: Mapping[str, Any], field: str) -> int:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise _blocked(f"UIA bridge returned an invalid {field}", "invalid_native_handle")
    return value


def _rect(payload: Mapping[str, Any], field: str) -> dict[str, int]:
    value = payload.get(field)
    if not isinstance(value, Mapping) or set(value) != set(RECT_FIELDS):
        raise _blocked(f"UIA bridge returned an invalid {field}", "invalid_rectangle")
    rectangle: dict[str, int] = {}
    for coordinate in RECT_FIELDS:
        item = value.get(coordinate)
        if isinstance(item, bool) or not isinstance(item, int):
            raise _blocked(
                f"UIA bridge returned a non-integer {field}.{coordinate}",
                "invalid_rectangle",
            )
        rectangle[coordinate] = item
    if (
        rectangle["right"] <= rectangle["left"]
        or rectangle["bottom"] <= rectangle["top"]
    ):
        raise _blocked(f"UIA bridge returned an empty {field}", "invalid_rectangle")
    return rectangle


def _validate_success(
    payload: dict[str, Any],
    *,
    window_title: str | None,
    process_name: str,
    canvas_name: str,
) -> dict[str, Any]:
    if payload.get("status") != "located":
        raise _blocked("UIA bridge did not report a located canvas", "invalid_json")

    actual_title = payload.get("window_title")
    if (
        not isinstance(actual_title, str)
        or not actual_title.strip()
        or "\x00" in actual_title
    ):
        raise _blocked("UIA bridge returned an invalid window title", "identity_mismatch")
    if window_title is not None and actual_title != window_title:
        raise _blocked("UIA bridge window title does not match the request", "identity_mismatch")
    actual_process = str(payload.get("process_name", "")).casefold().removesuffix(".exe")
    expected_process = process_name.casefold().removesuffix(".exe")
    if actual_process != expected_process:
        raise _blocked("UIA bridge process does not match the request", "identity_mismatch")
    if payload.get("canvas_name") != canvas_name or payload.get("control_type") != "Pane":
        raise _blocked("UIA bridge canvas identity does not match the request", "identity_mismatch")
    if payload.get("dpi_awareness") != "per-monitor-v2":
        raise _blocked("UIA bridge did not prove Per-Monitor V2 coordinates", "invalid_rectangle")
    if payload.get("window_rect_source") != "DWMWA_EXTENDED_FRAME_BOUNDS":
        raise _blocked("UIA bridge did not return DWM frame bounds", "invalid_rectangle")

    window_state_action = payload.get("window_state_action")
    window_restore_attempts = payload.get("window_restore_attempts")
    if (
        not isinstance(window_state_action, str)
        or window_state_action not in ("none", "restored-from-minimized")
    ):
        raise _blocked(
            "UIA bridge returned an invalid window_state_action",
            "invalid_window_state",
        )
    if (
        isinstance(window_restore_attempts, bool)
        or not isinstance(window_restore_attempts, int)
        or window_restore_attempts not in (0, 1)
    ):
        raise _blocked(
            "UIA bridge returned invalid window_restore_attempts",
            "invalid_window_state",
        )
    if (window_state_action, window_restore_attempts) not in (
        ("none", 0),
        ("restored-from-minimized", 1),
    ):
        raise _blocked(
            "UIA bridge returned inconsistent window restore metadata",
            "invalid_window_state",
        )

    top_hwnd = _positive_handle(payload, "top_hwnd")
    _positive_handle(payload, "canvas_hwnd")
    root_hwnd = payload.get("root_hwnd")
    if (
        isinstance(root_hwnd, bool)
        or not isinstance(root_hwnd, int)
        or root_hwnd <= 0
        or root_hwnd != top_hwnd
    ):
        raise _blocked(
            "Canvas native HWND does not resolve to the OSIS top-level HWND",
            "root_hwnd_mismatch",
        )

    window_rect = _rect(payload, "window_rect")
    canvas_rect = _rect(payload, "canvas_rect")
    overflow = {
        "left": max(0, window_rect["left"] - canvas_rect["left"]),
        "top": max(0, window_rect["top"] - canvas_rect["top"]),
        "right": max(0, canvas_rect["right"] - window_rect["right"]),
        "bottom": max(0, canvas_rect["bottom"] - window_rect["bottom"]),
    }
    if any(value > 2 for value in overflow.values()):
        raise _blocked(
            "Canvas rectangle is outside the DWM window bounds; "
            f"window_rect={window_rect}; canvas_rect={canvas_rect}; "
            f"overflow={overflow}",
            "invalid_rectangle",
            retryable=True,
        )
    raw_canvas_rect: dict[str, int] | None = None
    if any(overflow.values()):
        raw_canvas_rect = dict(canvas_rect)
        canvas_rect = {
            "left": max(canvas_rect["left"], window_rect["left"]),
            "top": max(canvas_rect["top"], window_rect["top"]),
            "right": min(canvas_rect["right"], window_rect["right"]),
            "bottom": min(canvas_rect["bottom"], window_rect["bottom"]),
        }
        if (
            canvas_rect["right"] <= canvas_rect["left"]
            or canvas_rect["bottom"] <= canvas_rect["top"]
        ):
            raise _blocked(
                "Canvas rectangle becomes empty after DPI boundary normalization",
                "invalid_rectangle",
            )

    result = dict(payload)
    result["top_hwnd"] = top_hwnd
    result["root_hwnd"] = root_hwnd
    result["window_rect"] = window_rect
    result["canvas_rect"] = canvas_rect
    result["source"] = "windows-uia"
    result["window_ref"] = f"hwnd:{top_hwnd}"
    result["canvas_ref"] = f"hwnd:{result['canvas_hwnd']}"
    if raw_canvas_rect is not None:
        result["canvas_rect_raw"] = raw_canvas_rect
        result["canvas_rect_adjustment"] = "clamped-to-window-within-2px"
    return result


def locate_canvas(
    *,
    window_title: str | None,
    process_name: str,
    canvas_name: str,
    timeout: float = DEFAULT_TIMEOUT,
    runner: Callable[..., Any] = subprocess.run,
) -> dict[str, Any]:
    """定位唯一 OSIS 画布并返回原生物理几何。

    ``runner`` 可注入，便于单元测试在不启动桌面自动化时验证传输和校验逻辑。
    """

    for label, value in (("process_name", process_name), ("canvas_name", canvas_name)):
        if not isinstance(value, str) or not value.strip() or "\x00" in value:
            raise ValueError(f"{label} must be a non-empty string without NUL")
    if window_title is not None and (
        not isinstance(window_title, str)
        or not window_title.strip()
        or "\x00" in window_title
    ):
        raise ValueError("window_title must be None or a non-empty string without NUL")
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not math.isfinite(float(timeout))
        or float(timeout) <= 0
    ):
        raise ValueError("timeout must be a finite positive number")

    script = _build_bridge_script(
        window_title=window_title,
        process_name=process_name,
        canvas_name=canvas_name,
    )
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    command: Sequence[str] = (
        "powershell.exe",
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-EncodedCommand",
        encoded,
    )
    for attempt in range(1, GEOMETRY_ATTEMPTS + 1):
        try:
            completed = runner(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="strict",
                timeout=float(timeout),
                check=False,
                shell=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except subprocess.TimeoutExpired as error:
            raise _blocked(
                f"UIA property bridge timed out after {float(timeout):g} seconds",
                "uia_timeout",
            ) from error
        except (OSError, subprocess.SubprocessError) as error:
            raise _blocked(
                f"Unable to start UIA property bridge: {error}",
                "powershell_failed",
            ) from error

        try:
            payload = _parse_payload(getattr(completed, "stdout", None))
        except UiaLocatorError:
            if getattr(completed, "returncode", 0) != 0:
                raise _blocked(
                    "PowerShell UIA property bridge failed without valid JSON",
                    "powershell_failed",
                )
            raise

        if payload.get("status") == "blocked":
            reason_code = payload.get("reason_code")
            if not isinstance(reason_code, str) or not reason_code:
                reason_code = "uia_blocked"
            message = payload.get("message")
            if not isinstance(message, str) or not message:
                message = f"UIA property bridge blocked: {reason_code}"
            if reason_code in SEMANTIC_REASON_CODES:
                raise _identity_error(message, reason_code)
            raise _blocked(message, reason_code)
        if getattr(completed, "returncode", 0) != 0:
            raise _blocked(
                "PowerShell UIA property bridge exited unsuccessfully",
                "powershell_failed",
            )

        try:
            return _validate_success(
                payload,
                window_title=window_title,
                process_name=process_name,
                canvas_name=canvas_name,
            )
        except UiaLocatorError as error:
            if not error.retryable or attempt == GEOMETRY_ATTEMPTS:
                raise
            time.sleep(GEOMETRY_RETRY_DELAY)

    raise AssertionError("unreachable UIA geometry retry state")


def discover_canvas(
    *,
    process_name: str = "Osis",
    canvas_name: str = "3D绘图",
    timeout: float = DEFAULT_TIMEOUT,
    runner: Callable[..., Any] = subprocess.run,
) -> dict[str, Any]:
    """按进程和 Pane 名发现唯一 OSIS 画布，不依赖预先声明的窗口标题。"""

    return locate_canvas(
        window_title=None,
        process_name=process_name,
        canvas_name=canvas_name,
        timeout=timeout,
        runner=runner,
    )
