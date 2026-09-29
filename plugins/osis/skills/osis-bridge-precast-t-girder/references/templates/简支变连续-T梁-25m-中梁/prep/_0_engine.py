"""模块级单例 OSISEngine,供同包内其他 prep 模块 import 使用。

不要在主代码里直接 new OSISEngine();通过 main.py 调度。
"""
from pyosis.core.engine import OSISEngine

engine = OSISEngine()
