"""osis-auto-testconformance/scripts/test_mechanics.py(受力评分)的指标与评分(纯计算,不连 OSIS)。"""

from __future__ import annotations

import importlib.util
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[1] / "skills"
spec = importlib.util.spec_from_file_location(
    "mechanics", SKILLS / "osis-auto-testconformance/scripts/test_mechanics.py")
mechanics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mechanics)


def _data(m_total: float, sx_max: float) -> dict:
    """10 m 简支梁两个单元 + 一根竖直桥墩;跨中恒载弯矩 100 kN·m,合计弯矩 m_total;反力 100 kN,自重 80 kN。"""
    force = lambda case, my: {"loadCase": case, "ele": 1, "node": 2, "my": my * 1e3}  # noqa: E731
    stress = lambda case, ele, sx: {"loadCase": case, "ele": ele, "point": "Max", "sxComp": sx * 1e6}  # noqa: E731
    return {
        "last": "CS2", "nodes": [[1, 0, 0, 0], [2, 5, 0, 0], [3, 10, 0, 0], [4, 0, 0, -8]],
        "elements": [[1, 1, 2], [2, 2, 3], [3, 4, 1]], "weight": 80e3,
        "support_reaction": [{"loadCase": "_合计_CS2", "no": 4, "fz": 60e3}, {"loadCase": "_合计_CS2", "no": 3, "fz": 40e3},
                             {"loadCase": "_恒载_CS2", "no": 3, "fz": 40e3}],
        "element_force": [force("_恒载_CS2", 100), force("_合计_CS2", m_total),
                          {"loadCase": "_恒载_CS2", "ele": 3, "node": 4, "my": 9e9}],  # 桥墩不算主梁
        "displacement": [{"loadCase": "_恒载_CS2", "no": 2, "uz": -0.01}, {"loadCase": "_恒载_CS2", "no": 4, "uz": -9.0}],
        "element_stress": [stress("_合计_CS2", 1, sx_max), stress("_合计_CS2", 1, -8.0), stress("_合计_CS1", 2, 1.0),
                           stress("_合计_CS2", 3, 99.0)],
        "long_stress": [stress("_合计_徐变十年", 1, -0.5), stress("_合计_徐变十年", 1, -7.0)],
    }


def _dims(items: list[dict]) -> list[str]:
    return [i["dim"] for i in items]


def test_good_model_passes():
    m = mechanics.metrics(_data(m_total=-20, sx_max=-1.0))
    assert round(m["balance"], 2) == 1.2 and m["reaction_sum"] == 100 and m["final_max"] == -1.0
    assert m["stage_max"] == 1.0 and m["stage_max_at"] == "CS1 单元 2"  # 桥墩的 99 MPa 不计
    assert m["weight_ratio"] == 1.25 and m["span"] == 10 and round(1 / m["sag"]) == 1000  # 桥墩节点的位移不计
    for tier, dims in (("fast", 5), ("stage", 7), ("full", 8)):
        items = mechanics.judge(m, tier, 50)
        assert _dims(items) == [f"D{k}" for k in range(1, dims + 1)] and min(i["score"] for i in items) == 1.0
    assert mechanics.judge(m, "fast", 30)[0]["score"] == 0.0  # 预应力构件 C30


def test_weak_prestress_fails():
    m = mechanics.metrics(_data(m_total=70, sx_max=2.5))  # 预应力只抵消 30%,成桥受拉
    items = {i["dim"]: i for i in mechanics.judge(m, "stage", 50)}
    assert items["D2"]["score"] == 0.0 and items["D2"]["advice"]
    assert items["D6"]["score"] == 0.0 and "拉应力" in items["D6"]["reason"]
    overall, text = mechanics.report("t", "stage", list(items.values()),
                                     {"stages": 5, "solved_stages": 3, "solve_s": 1.0, "grade": 50})
    assert overall == 0.0 and "不合格" in text and "### 6. D6 成桥应力" in text


def test_uplift_and_not_prestressed():
    data = _data(m_total=100, sx_max=-1.0)
    data["support_reaction"][1]["fz"] = -5e3
    items = mechanics.judge(mechanics.metrics(data), "fast", None, prestressed=False)
    assert _dims(items) == ["D3", "D4", "D5"] and items[0]["score"] == 0.5
    assert items[1]["score"] == 0.0  # 反力 55 kN ÷ 自重 80 kN = 0.69:自重没加全


def test_wrong_stiffness_and_double_gravity():
    data = _data(m_total=-20, sx_max=-1.0)
    data["displacement"][0]["uz"] = -0.2  # 挠跨比 1/50
    data["weight"] = 30e3  # 反力是自重的 3.3 倍
    items = {i["dim"]: i for i in mechanics.judge(mechanics.metrics(data), "fast", 50)}
    assert items["D5"]["score"] == 0.0 and "刚度偏小" in items["D5"]["reason"]
    assert items["D4"]["score"] == 0.0 and "重复计" in items["D4"]["reason"]
