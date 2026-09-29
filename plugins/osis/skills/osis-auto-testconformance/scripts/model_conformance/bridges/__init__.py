"""按桥型拆分的评分器。

层级:
  bridges/
    cantilever.py      悬浇变截面连续梁 (D1–D5)
    rigid_frame.py     变截面连续刚构 (D1–D6)
    t_girder.py        简支 T 梁 (D1–D4)
    small_box.py       简支小箱梁 (D1–D4)
    hollow_slab.py     简支空心板 (D1–D5)
    cast_in_place.py   现浇连续箱梁 (简化 5 维)
    unknown.py         未知桥型兜底
"""
from .cantilever import score_variable_section
from .cast_in_place import score_cast_in_place
from .hollow_slab import score_hollow_slab
from .rigid_frame import score_rigid_frame
from .small_box import score_small_box
from .t_girder import score_t_girder
from .unknown import score_unknown

__all__ = [
    "score_variable_section",
    "score_rigid_frame",
    "score_t_girder",
    "score_small_box",
    "score_hollow_slab",
    "score_cast_in_place",
    "score_unknown",
]
