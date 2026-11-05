// 模板界面:字符串大写转换(示例功能,替换为实际界面)。写法与 host 接口见 references/plugin_ui.md
import { createSignal, Show } from "solid-js"
import type { PluginProps } from "osis-plugin"

export const size = "small"

export default function Plugin(props: PluginProps) {
  const { host } = props
  const { Stack, TextField, Button, Card, Text, Log } = host.ui
  const [text, setText] = createSignal(host.storage.get<string>("text") ?? "")
  const [lines, setLines] = createSignal<string[]>([])
  const [output, setOutput] = createSignal("")
  const [error, setError] = createSignal("")
  const [busy, setBusy] = createSignal(false)

  const run = async () => {
    setBusy(true)
    setLines([])
    setOutput("")
    setError("")
    host.storage.set("text", text())
    const r = await host.python([text()], { onStdout: (l) => setLines((a) => [...a, l]) })
    setBusy(false)
    if (r.code !== 0) return setError(r.stderr.trim() || `退出码 ${r.code}`)
    setOutput((r.result as { output: string }).output)
  }

  return (
    <Stack gap={12}>
      <TextField label="文本" value={text()} onInput={setText} placeholder="输入要转换的文本" />
      <Button variant="primary" loading={busy()} disabled={!text()} onClick={run}>
        转换
      </Button>
      <Show when={lines().length}>
        <Log lines={lines()} maxHeight={120} />
      </Show>
      <Show when={output()}>
        <Card title="结果">
          <Text>{output()}</Text>
        </Card>
      </Show>
      <Show when={error()}>
        <Text variant="error">{error()}</Text>
      </Show>
    </Stack>
  )
}
