# 插件界面:ui.tsx 与 host 接口(v1)

插件界面写成 `ui.tsx`,在 OSIS-AI 界面里的插件窗口中渲染,用的是 OSIS-AI 自己的组件和配色,和主界面一体。
Python(`main.py`)只做后端:界面里用 `host.python()` 调它。

## 文件

```
~/.osisai/plugins/<id>/
  ui.tsx      必需。界面
  ui.css      可选。界面专用样式
  main.py     可选。后端逻辑(计算、读写文件、操作 OSIS),也是给 AI / 命令行用的 CLI
  icon.png
```

## ui.tsx 写法

SolidJS + TSX(不是 React):状态用 `createSignal`,读值要调用 `count()`,列表用 `<For>`,条件用 `<Show>`,
组件函数只执行一次(不要按 React 的重渲染思路写)。

```tsx
import { createSignal, Show } from "solid-js"
import type { PluginProps } from "osis-plugin"

export const size = "medium"          // 可选:窗口大小 small | medium | large | full,默认 medium

export default function Plugin(props: PluginProps) {
  const { host } = props
  const { Stack, NumberField, Button, Log } = host.ui
  const [span, setSpan] = createSignal<number | undefined>(host.storage.get("span") ?? 30)
  const [lines, setLines] = createSignal<string[]>([])
  const [busy, setBusy] = createSignal(false)

  const run = async () => {
    setBusy(true); setLines([])
    host.storage.set("span", span())
    const r = await host.python(["--span", String(span())], { onStdout: (l) => setLines((a) => [...a, l]) })
    setBusy(false)
    if (r.code !== 0) host.toast({ title: "运行失败", description: r.stderr, variant: "error" })
  }

  return (
    <Stack gap={12}>
      <NumberField label="跨径" unit="m" value={span()} onInput={setSpan} min={1} />
      <Button variant="primary" loading={busy()} onClick={run}>运行</Button>
      <Show when={lines().length}><Log lines={lines()} /></Show>
    </Stack>
  )
}
```

**import 只允许**:`solid-js`、`solid-js/store`、`solid-js/web`,以及 `import type`(类型导入编译时删掉)。
组件和能力全部从 `props.host` 取;不能 import npm 包、相对路径文件、Node 模块。要算东西、读写文件、调 OSIS,放进 `main.py`。

**样式**:优先用 `host.ui` 组件,自带配色和间距;布局用 `Stack`。需要自己写样式时用 `style={{ ... }}` 配合下面的
主题变量,或写 `ui.css`(类名加插件 id 前缀,避免影响主界面)。**不要用 Tailwind 类名**,插件里的类名不会被生成。

## host

```ts
type PluginProps = { host: PluginHost }

interface PluginHost {
  plugin: { id: string; name: string; dir: string }      // dir:插件目录绝对路径
  ui: UI                                                 // 见下表

  // 运行本插件的 main.py(~/.osisai/.venv 的 python,cwd = 插件目录,环境变量继承 OSIS-AI,能直接连当前 OSIS)。
  // stdout / stderr 按行实时回调;非零退出不抛异常,看 code。只有起不了进程才抛。
  // result:stdout 最后一个非空行能解析成 JSON 时给出解析结果,否则 undefined。
  python(args: string[], opts?: {
    onStdout?: (line: string) => void
    onStderr?: (line: string) => void
    signal?: AbortSignal                                 // abort 时结束整个进程树
  }): Promise<{ code: number; stdout: string; stderr: string; result?: unknown }>

  osis(cmd: string): Promise<{ success: boolean; message?: string }>   // 给当前 OSIS 发一段命令流

  pickFile(opts?: { title?: string; extensions?: string[]; startDir?: string }): Promise<string | undefined>
  pickFolder(opts?: { title?: string; startDir?: string }): Promise<string | undefined>
  openPath(path: string, opts?: { reveal?: boolean }): Promise<void>  // 系统默认程序打开;reveal=在资源管理器里选中
  fileUrl(path: string): string                                       // 本地文件的 URL,用于 <img src> 预览生成的图片

  toast(opts: { title: string; description?: string; variant?: "success" | "error" | "info" }): void
  ask(text: string, opts?: { send?: boolean }): void    // 把文字放进当前对话的输入框;send=true 直接发给 AI
  storage: { get<T = unknown>(key: string): T | undefined; set(key: string, value: unknown): void }  // 本插件持久存储
  close(): void                                          // 关闭插件窗口
}
```

## host.ui 组件

| 组件 | props |
|---|---|
| `Stack` | `direction?: "row" \| "col"`(默认 col)、`gap?: number`(px)、`align?`、`justify?`、`wrap?`、`children` |
| `Card` | `title?`、`children` |
| `Text` | `variant?: "body" \| "muted" \| "title" \| "error"`、`children` |
| `Button` | `variant?: "primary" \| "secondary" \| "ghost" \| "danger"`、`onClick`、`disabled?`、`loading?`、`children` |
| `TextField` | `label?`、`value`、`onInput(v: string)`、`placeholder?`、`multiline?`、`error?`、`disabled?` |
| `NumberField` | `label?`、`value: number \| undefined`、`onInput(v: number \| undefined)`、`min?`、`max?`、`step?`、`unit?`、`error?` |
| `Select` | `label?`、`value`、`options: { value: string; label: string }[]`、`onChange(v: string)` |
| `Checkbox` / `Switch` | `label`、`checked`、`onChange(v: boolean)` |
| `Slider` | `label?`、`value: number`、`onInput(v: number)`、`min`、`max`、`step?`、`format?(v: number): string`(右侧显示的数值,默认原值) |
| `ColorField` | `label?`、`value: string`(`#rrggbb`)、`onChange(v: string)`、`disabled?` —— 色块 + 取色器 + 十六进制输入 |
| `FileField` | `label?`、`value`、`onChange(path: string)`、`mode?: "file" \| "folder"`、`extensions?` —— 输入框 + 浏览按钮 |
| `Tabs` | `items: { label: string; content: JSX.Element }[]`、`value?`、`onChange?(index)` |
| `Table` | `columns: { key: string; label: string; align?: "left" \| "right" \| "center" }[]`、`rows: Record<string, unknown>[]` |
| `Log` | `lines: string[]` 或 `text: string`、`maxHeight?: number` —— 等宽滚动区,自动滚到底 |
| `Progress` | `value?: number`(0–1,不给为不定进度) |
| `Spinner` | — |
| `Markdown` | `text: string` |

主题变量(写自定义样式时用;取值随 OSIS-AI 明暗主题变化):

`--osis-plugin-bg`、`--osis-plugin-surface`、`--osis-plugin-border`、`--osis-plugin-text`、`--osis-plugin-text-muted`、
`--osis-plugin-accent`、`--osis-plugin-danger`、`--osis-plugin-success`、`--osis-plugin-radius`、`--osis-plugin-font-mono`

## main.py(后端)约定

- 纯命令行程序:argparse 收参数,不做界面,不 import tkinter / customtkinter
- 进度和日志逐行 `print(..., flush=True)` 到 stdout,界面用 `onStdout` 实时显示
- 结果:**最后一行打印一行 JSON**,界面从 `result` 读,如 `print(json.dumps({"output": path}, ensure_ascii=False))`
- 错误:写 stderr,退出码 1
- 同一个 main.py 也是给 AI / 命令行用的 CLI,保持参数自解释(`--help`)

## 检查

写完先编译检查 ui.tsx(和插件窗口用的是同一套编译):

```bash
"<OSIS-AI 安装目录>/opencode.exe" osis plugin-check ~/.osisai/plugins/<id>
```

无输出、退出码 0 即通过;有错误会打印行号和原因。
