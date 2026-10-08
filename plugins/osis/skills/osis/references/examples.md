# 端到端示例

下面的「调用」指 MCP 工具调用，工具都来自 `http://127.0.0.1:18080/mcp`。

## 1. 列出模型

**用户**：查看我当前打开的 OSIS 模型有哪些。

```text
list_instances()
→ {"instances": [
    {"instance_id":"A81F","project":"D:/bridge.sis","window_title":"bridge.sis",
     "version":"5.0","state":"ready"}
  ]}
```

回复用户：当前打开 1 个模型 `bridge.sis`（`D:/bridge.sis`），状态就绪。

## 2. 查节点数

**用户**：查看这个模型有多少节点。

```text
get_instance_info("A81F")           ← 单实例，直接用；state=ready
execute_python("A81F", "
from pyosis import OSISEngine
engine = OSISEngine()
print(engine.model_summary())
")
→ {"ok":true,"stdout":"...","stderr":"","result":null,
   "execution_time_ms":328,"exception":null}
```

## 3. API 不确定 → 先查再写

**用户**：给当前模型创建一个 XXX 类型单元。

```text
api_glob("engine.element.create_*")
→ {"ok":true,"total":5,"truncated":false,"matches":[
     "ElementManager.create_beam3d(self, no: 'int | None', node1: 'int', node2: 'int', mat: 'int', sec1: 'int', sec2: 'int', ...)  # 创建梁柱单元…",
     …]}

api_read("ElementManager.create_beam3d")
→ {"ok":true,"symbol":{"qualname":"ElementManager.create_beam3d","signature":"…",
     "doc":"…","params":[…],"source":"pyosis.element.manager:…"},
   "paths":["engine.element.create_beam3d"]}

execute_python("A81F", "
from pyosis import OSISEngine
engine = OSISEngine()
engine.element.create_beam3d(no=901, node1=1, node2=2, mat=1, sec1=1, sec2=1)
print('created', 901)
")
→ 若 ok=false，读 exception.traceback，对照 api_read 的签名修正重试
```

## 4. 多实例：改指定模型

**用户**：当前同时打开 bridge.osis 和 tower.osis。修改 bridge.osis 中的材料参数。

```text
list_instances()
→ A81F / D:/bridge.sis   ready
→ B92D / C:/project/tower.sis   busy

api_grep("弹性模量")                ← 定位材料相关 API，再 api_read
execute_python("A81F", "...")     ← 全程只用 A81F
execute_python("A81F", "从模型读回材料验证 ...")
→ 报告：在 bridge.sis 上改了 C30 → C40，已读回确认
```

## 5. 模糊多实例 → 反问

**用户**：修改当前模型。

```text
list_instances()
→ 两个实例，project 分别是 bridge.sis / tower.sis，无法判断
```

用提问工具问（宿主没有就普通文本）：

> 当前有两个 OSIS 模型：`bridge.sis`(D:/bridge.sis) 和 `tower.sis`(C:/project/tower.sis)。你要改哪一个？

## 6. 异常恢复

```text
execute_python("A81F", "engine.element.create_beam3d(no=1, node1=1, node2=2, mat=1, sec1=1)")
→ ok=false, exception.type="TypeError",
  exception.message="create_beam3d() missing 1 required positional argument: 'sec2'"

api_read("ElementManager.create_beam3d")
→ 补上 sec2

execute_python("A81F", "修正后的脚本")
→ ok=true

execute_python("A81F", "查询验证该单元存在")
→ 报告
```

**超时/异常后先读回再重试**：`EXECUTION_TIMEOUT` 只停了本地子进程，OSIS 端可能
已受理部分操作。先查询读回确认实际结果，再决定是否重试 —— 不要直接重跑创建命令。

## 7. 完整建模（写回 + 评测）

**用户**：按 30+50+30 悬浇连续梁建一座桥。

```text
list_instances()                      → A81F
读 osis-engine SKILL                   → 路由到 osis-bridge-cantilever-box
读模板 references/templates/...        → 复制到 <project>/py/prep/
execute_python("A81F", file="py/prep/main.py", cwd="D:/proj")   → 写回
execute_python("A81F", "
from pyosis import OSISEngine
engine = OSISEngine()
print(engine.model_summary())
")                                     → 验证
按 osis-auto-testconformance 做构造评测 → 报告
```

## 8. 实例闪退

```text
execute_python("B92D", "...")
→ {"ok":false,"error":{"code":"INSTANCE_OFFLINE", ...}}

list_instances()
→ B92D 已消失，A81F 仍在
```

告知用户 tower.osis 的 OSIS 实例已离线，重新打开后需重新选择实例（ID 会变）。

## 9. Broker 未启动

```text
list_instances()
→ MCP 连接失败
```

```
OSIS Agent Broker 当前不可连接。
请确认 OSIS Agent 服务已启动。
```

## 10. 高级：raw_http_request

仅在 MCP 工具覆盖不到、需要直接打 OSIS 原生 HTTP 接口时使用：

```text
raw_http_request(instance_id="A81F", method="GET", path="/status")
```

不要把它当作日常工作流。用户永远不需要知道真实端口 —— Broker 负责路由。
