---
name: osis-l0-hot
description: 已停用。不要加载。改 py 后的写回一律跑 prep/main.py,见 osis-engine。
---

# osis-l0-hot

已停用。不要调用本技能,不要跑 `scripts/l0_hot.py`。

改了 `py/` 要进 OSIS 时,按 `osis-engine` 跑 `prep/main.py`。只求解、不改模型时用 `OSISEngine().solve()`。
