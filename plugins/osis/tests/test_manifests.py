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


# ---------------------------------------------------------------- Codex 侧 §16


def test_codex_portable_manifest():
    m = load("plugin.json")
    assert m["$schema"] == "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
    assert KEBAB.match(m["name"]), "plugin name 必须 kebab-case"
    assert m["name"] == "osis"
    assert m.get("version")
    assert m.get("description")


def test_codex_mcp_config():
    c = load("mcp.json")
    assert c["$schema"] == "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"
    srv = c["mcpServers"]["osis"]
    assert srv["type"] == "streamable-http"
    assert srv["url"] == f"http://127.0.0.1:{BROKER_PORT}{MCP_PATH}"


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
    srv = c["mcpServers"]["osis"]
    # Claude Code 中 url 必须显式带 type,否则被当成 stdio server
    assert srv["type"] in ("http", "streamable-http")
    assert srv["url"] == f"http://127.0.0.1:{BROKER_PORT}{MCP_PATH}"


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


# ---------------------------------------------------------------- MCP 配置一致 §14


def test_mcp_endpoints_agree():
    a = load("mcp.json")["mcpServers"]["osis"]["url"]
    b = load(".mcp.json")["mcpServers"]["osis"]["url"]
    assert a == b, "Codex 与 Claude 必须连同一个 Broker endpoint"


def test_mcp_servers_agree():
    """两侧 MCP 只差格式(type 写法),server 集合与 stdio 启动方式必须一致。"""
    a, b = load("mcp.json")["mcpServers"], load(".mcp.json")["mcpServers"]
    assert a.keys() == b.keys()
    # 插件根目录占位符两侧写法不同:Codex(Agent Plugins 规范)${PLUGIN_ROOT},Claude ${CLAUDE_PLUGIN_ROOT}
    claude_args = lambda s: [x.replace("${CLAUDE_PLUGIN_ROOT}", "${PLUGIN_ROOT}") for x in s.get("args", [])]
    for name in a:
        for key in ("command", "env"):
            assert a[name].get(key) == b[name].get(key), f"{name}.{key} 两侧不一致"
        assert a[name].get("args", []) == claude_args(b[name]), f"{name}.args 两侧不一致"


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
    assert (PLUGIN_ROOT / "skills" / "osis" / "SKILL.md").is_file()
    dirs = [p for p in (PLUGIN_ROOT / "skills").iterdir() if p.is_dir()]
    assert len(dirs) >= 1
    for d in dirs:
        assert (d / "SKILL.md").is_file(), f"{d.name} 缺 SKILL.md"


def test_core_skill_frontmatter():
    text = (PLUGIN_ROOT / "skills" / "osis" / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\n")
    head = text.split("---", 2)[1]
    assert re.search(r"^name:\s*osis\s*$", head, re.M), "核心 skill name 必须是 osis"
    assert re.search(r"^description:\s*\S", head, re.M), "description 不能为空"


def test_core_skill_declares_all_tools():
    text = (PLUGIN_ROOT / "skills" / "osis" / "SKILL.md").read_text(encoding="utf-8")
    for tool in ("list_instances", "get_instance_info", "api_glob", "api_grep", "api_read", "execute_python"):
        assert tool in text, f"核心 skill 未提及 {tool}"


def test_core_skill_covers_required_rules(  # 开发要求 §12 十条铁律
):
    text = (PLUGIN_ROOT / "skills" / "osis" / "SKILL.md").read_text(encoding="utf-8")
    checks = {
        "不要猜测 API": "猜测 OSIS API",
        "先查 API": "不确定 API 时先用",
        "显式 instance_id": "instance_id",
        "多实例询问": "歧义",
        "Python 优先": "Python",
        "单一任务": "一个明确任务",
        "结果验证": "验证",
        "读 traceback": "traceback",
        "不因失败否定": "不支持",
        "不暴露端口": "端口",
    }
    missing = [k for k, v in checks.items() if v not in text]
    assert not missing, f"核心 skill 缺少必备规则: {missing}"


def test_core_skill_references_files_exist():
    ref_dir = PLUGIN_ROOT / "skills" / "osis" / "references"
    for name in ("concepts.md", "common-workflows.md", "troubleshooting.md", "examples.md"):
        assert (ref_dir / name).is_file(), f"references/{name} 缺失"


def test_skill_count():
    dirs = sorted(p.name for p in (PLUGIN_ROOT / "skills").iterdir() if p.is_dir())
    assert "osis" in dirs, "必须有核心 skill osis"
    assert len(dirs) >= 20, f"领域 skill 复制不完整: {len(dirs)}"


# ---------------------------------------------------------------- 布局 §15


def test_expected_layout():
    for rel in (
        "plugin.json",
        "mcp.json",
        ".mcp.json",
        ".claude-plugin/plugin.json",
        "README.md",
        "skills/osis/SKILL.md",
    ):
        assert (PLUGIN_ROOT / rel).exists(), f"缺少 {rel}"
    for rel in (".agents/plugins/marketplace.json", ".claude-plugin/marketplace.json"):
        assert (REPO_ROOT / rel).exists(), f"缺少 {rel}"


# ---------------------------------------------------------------- 领域 skill 单向同步


SRC_SKILLS = REPO_ROOT.parent / "osis-skill-enhance" / ".agents" / "skills"


def _tree(root: Path) -> dict[str, bytes]:
    # 统一换行:两个仓库的 autocrlf / .gitattributes 可能不同
    return {
        p.relative_to(root).as_posix(): p.read_bytes().replace(b"\r\n", b"\n")
        for p in root.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    }


def test_synced_skills_recorded():
    stamp = (PLUGIN_ROOT / "skills" / ".synced-from").read_text(encoding="utf-8")
    names = stamp.split("skills:", 1)[1].split()
    assert "osis" not in names
    for n in names:
        assert (PLUGIN_ROOT / "skills" / n / "SKILL.md").is_file(), n


def test_synced_skills_match_source():
    """插件侧不许手改领域 skill:改源仓库再跑 scripts/sync_skills.py。"""
    if not SRC_SKILLS.is_dir():
        pytest.skip("未检出 osis-skill-enhance,跳过同步一致性检查")
    stamp = (PLUGIN_ROOT / "skills" / ".synced-from").read_text(encoding="utf-8")
    stale = []
    for n in stamp.split("skills:", 1)[1].split():
        if _tree(SRC_SKILLS / n) != _tree(PLUGIN_ROOT / "skills" / n):
            stale.append(n)
    assert not stale, f"与源仓库不一致(先跑 scripts/sync_skills.py): {stale}"


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
    """key 不进仓库(公开):由 scripts/weknora_launch.py 从环境变量 / Windows 用户变量读。"""
    leaked = [p.name for p in PLUGIN_ROOT.rglob("*.json") if re.search(r"sk-[A-Za-z0-9_-]{20,}", p.read_text(encoding="utf-8"))]
    assert not leaked, f"配置里出现了 API key: {leaked}"


def test_weknora_launch_key_order(monkeypatch):
    import importlib.util

    spec = importlib.util.spec_from_file_location("weknora_launch", PLUGIN_ROOT / "scripts" / "weknora_launch.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "user_env", lambda name: "from-registry")
    monkeypatch.setenv("WEKNORA_API_KEY", "from-env")
    assert mod.api_key() == "from-env"
    monkeypatch.delenv("WEKNORA_API_KEY")
    assert mod.api_key() == "from-registry"
    monkeypatch.setattr(mod, "user_env", lambda name: "")
    assert mod.api_key() == ""  # 没 key 也能启动
