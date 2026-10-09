"""把 osis-skill-enhance 的 .agents/skills 原样镜像到 plugins/osis/skills。

单向同步,插件侧不手改领域 skill(要改去 osis-skill-enhance 改,再跑本脚本)。

    python scripts/sync_skills.py                       # 默认源:../osis-skill-enhance/.agents/skills
    python scripts/sync_skills.py --src D:/xx/.agents/skills
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEST = REPO / "plugins" / "osis" / "skills"
DEFAULT_SRC = REPO.parent / "osis-skill-enhance" / ".agents" / "skills"

STAMP = ".synced-from"
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc")


def synced_names(src: Path) -> list[str]:
    return sorted(p.name for p in src.iterdir()
                  if p.is_dir() and (p / "SKILL.md").is_file())


def source_commit(src: Path) -> str:
    try:
        out = subprocess.run(["git", "-C", str(src), "rev-parse", "HEAD"],
                             capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(src), "status", "--porcelain", "."],
                               capture_output=True, text=True, check=True).stdout.strip()
        return out + (" (dirty)" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC)
    src = ap.parse_args().src.resolve()
    if not src.is_dir():
        raise SystemExit(f"源目录不存在: {src}")

    names = synced_names(src)
    for old in DEST.iterdir():
        if old.is_dir() and old.name not in names:
            shutil.rmtree(old)
            print(f"删除: {old.name}")
    for name in names:
        shutil.rmtree(DEST / name, ignore_errors=True)
        shutil.copytree(src / name, DEST / name, ignore=IGNORE)
    (DEST / STAMP).write_text(
        f"source: osis-skill-enhance/.agents/skills\ncommit: {source_commit(src)}\n"
        f"skills: {' '.join(names)}\n",
        encoding="utf-8",
    )
    print(f"已同步 {len(names)} 个 skill ← {src}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
