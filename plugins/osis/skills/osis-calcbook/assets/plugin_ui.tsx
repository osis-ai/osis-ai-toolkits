// 计算书插件界面:为当前打开的 OSIS 项目生成计算书。逻辑在 main.py,这里只负责运行、显示进度和结果
import { createSignal, Show } from "solid-js"
import type { PluginProps } from "osis-plugin"

export const size = "medium"

type Result = { output: string; report: string }

export default function Plugin(props: PluginProps) {
  const { host } = props
  const { Stack, Text, Button, Log, Card, Progress } = host.ui
  const [lines, setLines] = createSignal<string[]>([])
  const [busy, setBusy] = createSignal(false)
  const [result, setResult] = createSignal<Result>()
  const [error, setError] = createSignal("")

  const run = async () => {
    setBusy(true)
    setLines([])
    setResult(undefined)
    setError("")
    const r = await host.python([], { onStdout: (l) => setLines((a) => [...a, l]) })
    setBusy(false)
    if (r.code !== 0) return setError(r.stderr.trim() || `退出码 ${r.code}`)
    setResult(r.result as Result)
    host.toast({ title: "计算书已生成", variant: "success" })
  }

  const check = () =>
    host.ask(`帮我检查刚生成的计算书 ${result()!.output}:红字【待填写】处还缺什么、数据是否和模型一致。`, {
      send: true,
    })

  return (
    <Stack gap={12}>
      <Text variant="muted">为当前打开的 OSIS 项目生成计算书(需已完成验算),结果保存在项目目录。</Text>
      <Stack direction="row" gap={8}>
        <Button variant="primary" loading={busy()} onClick={run}>
          生成计算书
        </Button>
      </Stack>
      <Show when={busy()}>
        <Progress />
      </Show>
      <Show when={lines().length}>
        <Log lines={lines()} maxHeight={160} />
      </Show>
      <Show when={result()}>
        {(r) => (
          <Card title="已生成">
            <Stack gap={8}>
              <Text>{r().output}</Text>
              <Log text={r().report} maxHeight={200} />
              <Text variant="muted">红字【待填写】处需人工补充。</Text>
              <Stack direction="row" gap={8} wrap>
                <Button variant="primary" onClick={() => host.openPath(r().output)}>
                  打开计算书
                </Button>
                <Button variant="secondary" onClick={() => host.openPath(r().output, { reveal: true })}>
                  打开所在文件夹
                </Button>
                <Button variant="ghost" onClick={check}>
                  让 AI 检查
                </Button>
              </Stack>
            </Stack>
          </Card>
        )}
      </Show>
      <Show when={error()}>
        <Card title="生成失败">
          <Text variant="error">{error()}</Text>
        </Card>
      </Show>
    </Stack>
  )
}
