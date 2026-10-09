"""启动 weknora MCP server。

key 不写进插件配置:先用进程环境变量 WEKNORA_API_KEY;没有就读 Windows 用户环境变量
(`setx WEKNORA_API_KEY ...` 写在注册表 HKCU\\Environment,Codex 不把它传给 MCP 子进程);
都没有也照常启动,只是知识库工具会报鉴权失败,插件其余功能不受影响。
"""
from __future__ import annotations

import os
import runpy

KEY = "WEKNORA_API_KEY"


def user_env(name: str) -> str:
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            return str(winreg.QueryValueEx(k, name)[0])
    except (ImportError, OSError):  # 非 Windows,或没设置
        return ""


def api_key() -> str:
    return os.environ.get(KEY) or user_env(KEY)


if __name__ == "__main__":
    os.environ[KEY] = api_key()  # weknora_mcp_server 在 import 时读 key,必须先设好
    runpy.run_module("weknora_mcp_server", run_name="__main__", alter_sys=True)
