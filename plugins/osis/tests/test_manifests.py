"""插件结构与 manifest 校验 —— 开发要求 §15 / §16 / §17 / §18。

只依赖标准库,从任意工作目录都能跑:
    python -m pytest plugins/osis/tests -q
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parents[1]      # plugins/osis
REPO_ROOT = PLUGIN_ROOT.parents[1]                     # 仓库根
BROKER_PORT = 18080
MCP_PATH = f"/mcp"


def load(rel: str) -> dict:
    return json.loads((PLUGIN_ROOT / rel).read_text(encoding="utf-8"))


def repo_load(rel: str) -> dict:
    return json.loads((REPO_ROOT / rel).read_text(encoding="utf-8"))


KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def assert_osis_stdio(srv: dict) -> None:
    """osis 走 stdio:Broker 的 --stdio 自动拉起/复用 18080 上的 Broker 再转发。
    用 OSIS 环境的 Python;cmd /c 负责展开 %USERPROFILE%(Codex 不展开 command 里的变量);
    -P 防止宿主项目目录(cwd)里的同名 .py 盖掉依赖。"""
    assert srv["type"] == "stdio"
    assert srv["command"] == "cmd"
    assert srv["args"] == ["/c", r"%USERPROFILE%\.osisai\.venv\Scripts\python.exe", "-P", "-m", "osis_broker", "--stdio"]


# ---------------------------------------------------------------- Codex 侧 §16


def test_codex_portable_manifest():
    m = load("plugin.json")
    assert m["$schema"] == "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
    assert KEBAB.match(m["name"]), "plugin name 必须 kebab-case"
    assert m["name"] == "osis"
    assert m.get("version")
    assert m.get("description")


def test_codex_icons_exist():
    ui = load("plugin.json")["extensions"]["com.openai"]["interface"]
    for key in ("composerIcon", "logo"):
        assert ui[key].startswith("./") and (PLUGIN_ROOT / ui[key][2:]).is_file(), key


def test_codex_mcp_config():
    c = load("mcp.json")
    assert c["$schema"] == "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"
    assert_osis_stdio(c["mcpServers"]["osis"])


def test_codex_marketplace():
    mk = repo_load(".agents/plugins/marketplace.json")
    assert mk["name"] == "osis-ai-toolkits"
    entries = {p["name"]: p for p in mk["plugins"]}
    assert "osis" in entries
    src = entries["osis"]["source"]
    assert src["source"] == "local"
    # Codex 解析 source.path 时以 marketplace 根为基准
    assert src["path"] == "./plugins/osis"
    assert (REPO_ROOT / src["path"][2:]).is_dir(), "marketplace source.path 必须存在"
    assert entries["osis"]["policy"]["installation"] in ("AVAILABLE", "INSTALLED_BY_DEFAULT")
    assert "category" in entries["osis"]


# ---------------------------------------------------------------- Claude 侧 §17


def test_claude_manifest():
    m = load(".claude-plugin/plugin.json")
    assert KEBAB.match(m["name"]), "Claude plugin name 必须 kebab-case"
    assert m["name"] == "osis"
    assert m.get("version")
    assert m.get("description")


def test_claude_mcp_config():
    c = load(".mcp.json")
    assert_osis_stdio(c["mcpServers"]["osis"])


def test_claude_marketplace():
    mk = repo_load(".claude-plugin/marketplace.json")
    assert KEBAB.match(mk["name"])
    assert mk["owner"]["name"]
    entries = {p["name"]: p for p in mk["plugins"]}
    assert "osis" in entries
    # source 相对 marketplace 根,且不能用 ..
    src = entries["osis"]["source"]
    assert src.startswith("./") and ".." not in src
    assert (REPO_ROOT / src[2:]).is_dir()
    # 入口名必须与 manifest 名一致,否则 /plugin install osis@... 找不到
    assert entries["osis"]["name"] == load(".claude-plugin/plugin.json")["name"]


def test_both_marketplaces_share_same_plugin():
    codex = repo_load(".agents/plugins/marketplace.json")
    claude = repo_load(".claude-plugin/marketplace.json")
    assert {p["name"] for p in codex["plugins"]} == {p["name"] for p in claude["plugins"]}


# ---------------------------------------------------------------- 其他宿主
# ZCode / WorkBuddy(CodeBuddy)直接读 Claude 那套,不另写。


def assert_same_servers(servers: dict) -> None:
    """各宿主只差格式,server 集合与启动命令/env 必须与 Claude 那份一致。"""
    ref = load(".mcp.json")["mcpServers"]
    assert servers.keys() == ref.keys()
    for name in ref:
        for key in ("command", "args", "env"):
            assert servers[name].get(key) == ref[name].get(key), f"{name}.{key} 与 .mcp.json 不一致"


def test_kimi_manifest():
    m = repo_load("kimi.plugin.json")  # 从仓库根安装,路径相对仓库根
    assert m["name"] == "osis"
    assert (REPO_ROOT / m["skills"][2:]).resolve() == (PLUGIN_ROOT / "skills").resolve()
    assert_same_servers(m["mcpServers"])


def test_minimax_manifest():
    m = load(".minimax-plugin/plugin.json")
    assert m["schemaVersion"] == 1 and m["name"] == "osis"
    assert (PLUGIN_ROOT / m["icon"]).is_file()
    dirs = sorted(p.name for p in (PLUGIN_ROOT / "skills").iterdir() if p.is_dir())
    assert m["skills"] == [f"skills/{d}/SKILL.md" for d in dirs], "增删 skill 后同步 .minimax-plugin/plugin.json"
    assert len(m["mcpServers"]) == 1
    c = load(m["mcpServers"][0])
    assert c["schemaVersion"] == 1
    assert_same_servers(c["mcpServers"])


def test_qoder_manifest_and_marketplace():
    m = load(".qoder-plugin/plugin.json")
    assert m["name"] == "osis"
    assert_same_servers(m["mcpServers"])
    mk = repo_load(".qoder-plugin/marketplace.json")
    assert mk == {**repo_load(".claude-plugin/marketplace.json"), "metadata": mk["metadata"]}


def test_versions_agree():
    versions = {
        "plugin.json": load("plugin.json")["version"],
        ".claude-plugin": load(".claude-plugin/plugin.json")["version"],
        ".qoder-plugin": load(".qoder-plugin/plugin.json")["version"],
        ".minimax-plugin": load(".minimax-plugin/plugin.json")["version"],
        "kimi.plugin.json": repo_load("kimi.plugin.json")["version"],
    }
    assert len(set(versions.values())) == 1, f"版本号不一致: {versions}"


# ---------------------------------------------------------------- MCP 配置一致 §14


def test_mcp_servers_agree():
    """两侧 MCP 只差格式(type 写法),server 集合与 stdio 启动方式必须一致。"""
    a, b = load("mcp.json")["mcpServers"], load(".mcp.json")["mcpServers"]
    assert a.keys() == b.keys()
    for name in a:
        for key in ("command", "args", "env"):
            assert a[name].get(key) == b[name].get(key), f"{name}.{key} 两侧不一致"


def test_broker_port_consistent_across_repo():
    """端口写死在多处,必须一致(改端口要全部同步)。"""
    expected = f"127.0.0.1:{BROKER_PORT}"
    hits = []
    for path in list(PLUGIN_ROOT.rglob("*.json")) + list(PLUGIN_ROOT.rglob("*.md")):
        if "node_modules" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"127\.0\.0\.1:(\d{4,5})", text):
            hits.append((path.relative_to(REPO_ROOT).as_posix(), m.group(1)))
    wrong = [h for h in hits if h[1] != str(BROKER_PORT)]
    assert not wrong, f"发现不一致的 Broker 端口: {wrong}"


# ---------------------------------------------------------------- Skill §12 / §15


def test_single_source_of_skill():
    """skills/ 是唯一 Skill 源,Codex 与 Claude 共用同一份(禁止两套)。"""
    dirs = [p for p in (PLUGIN_ROOT / "skills").iterdir() if p.is_dir()]
    assert len(dirs) >= 1
    for d in dirs:
        assert (d / "SKILL.md").is_file(), f"{d.name} 缺 SKILL.md"


def test_skill_count():
    dirs = sorted(p.name for p in (PLUGIN_ROOT / "skills").iterdir() if p.is_dir())
    assert "osis" not in dirs, "使用规矩在 Broker 的 MCP instructions 里,不要再加 osis skill"
    assert len(dirs) >= 20, f"领域 skill 复制不完整: {len(dirs)}"


# ---------------------------------------------------------------- 布局 §15


def test_expected_layout():
    for rel in (
        "plugin.json",
        "mcp.json",
        ".mcp.json",
        ".claude-plugin/plugin.json",
        "README.md",
    ):
        assert (PLUGIN_ROOT / rel).exists(), f"缺少 {rel}"
    for rel in (".agents/plugins/marketplace.json", ".claude-plugin/marketplace.json"):
        assert (REPO_ROOT / rel).exists(), f"缺少 {rel}"


# ---------------------------------------------------------------- 可选:连通性


def test_broker_endpoint_reachable_if_running():
    """Broker 在跑时才验证 MCP 可连;未跑则跳过(插件本身不自带 Broker)。"""
    import httpx

    url = f"http://127.0.0.1:{BROKER_PORT}/health"
    try:
        r = httpx.get(url, timeout=1.5)
    except Exception as exc:
        pytest.skip(f"Broker 未运行({exc.__class__.__name__}),跳过连通性检查")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["mcp"] == MCP_PATH


# ---------------------------------------------------------------- WeKnora key


def test_no_api_key_in_plugin_files():
    """key 不进仓库(公开):weknora_mcp_server 从环境变量 WEKNORA_API_KEY 读,没有也能启动。"""
    leaked = [p.name for p in PLUGIN_ROOT.rglob("*.json") if re.search(r"sk-[A-Za-z0-9_-]{20,}", p.read_text(encoding="utf-8"))]
    assert not leaked, f"配置里出现了 API key: {leaked}"
