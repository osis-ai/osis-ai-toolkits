---
name: osis-l0-hot
description: 已停用。不要加载。改 py 后的写回一律跑 prep/main.py,见 osis-engine。
---

# osis-l0-hot

已停用。不要调用本技能,不要跑 `scripts/l0_hot.py`。

改了 `py/` 要进 OSIS 时,按 `osis-engine` 用 `execute_python(file=".../prep/main.py", cwd="<project_dir>")` 写回。只求解、不改模型时用 `OSISEngine().solve()`。
