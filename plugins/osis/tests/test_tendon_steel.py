"""osis-check/scripts/tendon_steel.py 用模板 prep 校核用钢量统计。"""

from __future__ import annotations

import importlib.util
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[1] / "skills"
spec = importlib.util.spec_from_file_location("tendon_steel", SKILLS / "osis-check/scripts/tendon_steel.py")
tendon_steel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tendon_steel)


def test_cantilever_template_steel():
    prep = SKILLS / "osis-bridge-cantilever-box/references/templates/变截面悬浇连续梁-65+120+65/prep"
    rows, shared, missing = tendon_steel.summarize(prep)
    assert not missing
    assert sum(r["根数"] for r in rows.values()) == 4900
    assert round(sum(r["用钢量"] for r in rows.values()), 1) == 265.8
    assert shared == {"15-19": ["BT", "ZT"], "15-20": ["BB", "T"], "15-21": ["F", "ZB"]}


def test_area_form_prop():
    # 现浇箱梁模板用 area=0 直接给面积的写法
    prep = SKILLS / "osis-bridge-conventional-box/references/templates/现浇等截面箱梁-25+25-单箱单室-9/prep"
    rows, _, missing = tendon_steel.summarize(prep)
    assert not missing and sum(r["根数"] for r in rows.values()) == 180
