---
name: osis-customize-osisai
description: >
  为用户创建或修改 OSIS-AI 自定义插件与自定义 skill。
  凡用户想把固定流程固化成可复用工具(固定的模型导入、结果导出、批量处理、格式转换、
  计算小工具),提到"做个插件""写个插件""加个工具""把这个流程固化",或想把灵活流程
  沉淀为 skill("新建个 skill""把这个流程做成 skill"),或要求修改/删除已有插件与 skill,
  或抱怨某官方 skill 不好用、要改官方 skill,  或要把当前模型入库("模型入库""做成模板"
  "加入模板库""把这座桥存成模板""以后基于这个模型改")时,都用本技能。包含插件契约
  (%USERPROFILE%\.osisai\plugins、main.py 的 --ui/CLI 双模式、plugins.json 注册、
  icon.png 图标生成)与 skill 编写规范(用户 skill 只写
  %USERPROFILE%\.osisai\.agents\skills;同名整份替换官方,禁止改安装包)。
---

# osis-customize-osisai

帮用户扩展 OSIS-AI。两条路:**固定流程 → 插件**(确定性代码,一次写对,以后传参即用);**灵活流程 → skill**(一份指导文档,AI 以后照着现场干活)。

**改官方 skill 走 §改官方 skill**:先整目录复制到用户态,再只改副本。禁止改安装包。**模型入库走 §模型入库**。

## 用户态目录与覆盖规则

用户可写目录只在 `~/.osisai`(`%USERPROFILE%\.osisai`)。**禁止改 OSIS 安装包里的官方 skill。**

| 用途 | 路径 |
|---|---|
| 用户插件 | `~/.osisai/plugins/`(`plugins.json` + `requirements.txt` + 各插件目录) |
| 用户 skill | `~/.osisai/.agents/skills/<name>/` |
| 官方 skill | 安装包内,只读 |

**同名覆盖=整份替换,不是按文件合并。** 用户目录一旦出现 `<name>`,运行时只用这一份,官方同名里的 `references/`、`scripts/` 等**不会**补缺。因此改官方 skill 必须先把官方整目录复制到用户态,再改副本。复制用 `Path.resolve()` 拷真实文件,不要拷成链接。找不到官方目录就 `ls`,不要猜盘符。

## 先决策:插件还是 skill

| | 形态 | 适合 | 判据 |
|---|---|---|---|
| 插件 | `~/.osisai/plugins/<英文名>/main.py`,Python 程序 | 流程确定:固定格式的导入/导出、批量处理、计算、转换 | 全部逻辑能一次写进 main.py,以后只靠传参就能用 |
| skill | `~/.osisai/.agents/skills/<英文名>/SKILL.md`,给 AI 的指导文档 | 流程灵活:要按环境试错,如特殊构型桥梁建模 | 每次都要 AI 看中间结果、改代码、再跑 |

一句话自问:**"这个流程以后每次都要 AI 现场写代码吗?"** 不用 → 插件;用 → skill。

用户说的是已有**官方** skill 不好用 → 走 §改官方 skill。用户要把当前桥做成模板 / 加入模板库 / 以后基于这座桥再改 → §模型入库。

## 创建插件(七步)

### 1. 建目录

`~/.osisai/plugins/<英文名>/`。英文名小写、简短、望文生义(现有插件:icon)。目录名即插件 ID,plugins.json 与命令路径都用它,起名后不再改。若 `plugins/` 或 `plugins.json` 还不存在:建目录,写入 `[]` 作为 `~/.osisai/plugins/plugins.json`,需要第三方依赖时再建空的 `~/.osisai/plugins/requirements.txt`。

### 2. 写 main.py —— 调用契约

插件有两类调用方,**输出契约**:

- **插件管理 UI**(用户在 OSIS-AI 界面点开插件):固定 `python main.py --ui`,**不传任何其他参数**。**只在出错时抓 stderr 弹错误框**(error+exitCode+stderr 结构化文本,带 [复制全部])。**正常结果由插件自己的 GUI 窗口显示**(A 形态);B 形态被误点开时也是把用法打到 stderr 让 UI 弹框(详见下面 B 形态)
- **CLI**(AI 或其他工具代替用户调用;本技能生成图标就是调 icon 插件的 CLI):`python main.py <参数>`,成功结果从 stdout 读;stderr 留给错误

据此选一种形态:

**A. GUI 插件**(参数要用户每次改,或要看丰富的结果):

- `--ui` 或无参数 → GUI,用合适的界面库,可现场装 (已预装customtkinter);窗口里正常显示结果
- 传其他参数 → CLI(argparse),成功结果写 stdout,错误写 stderr
- **正常结果交给 GUI 自己渲染;不要把结果打印到 stderr**——stderr 留给错误,UI 会把它当异常显示给用户

**B. 纯 CLI 插件**(参数可以写死/有合理默认值):不做界面,但必须**忽略 `--ui`**——剥掉它后按 CLI 处理,且所有参数都带默认值,保证无参调用也能跑:

```python
def main() -> int:
    args = sys.argv[1:]
    if args and args[0] == "--ui":
        args = args[1:]    # 无 GUI:忽略插件系统传来的 --ui
    return run_cli(args)   # 无参时走 argparse 默认值
```

**B 形态被插件管理器 UI 误点开时**:用户点了插件但参数不该从 UI 来——插件无参,跑出用法自说明(docstring + 示例)打到 stderr 并返回非零。这样 UI 会弹出错误框,用户能看到这个插件没有界面、要在命令行怎么用。**注意:这跟"真正的错误"是两回事,但都用 stderr 通道让 UI 弹框**——所以是无参分支选 stderr,而不是"正常结果也走 stderr"这种通用契约。

两种形态的 CLI 都遵守:成功结果写 stdout(给 CLI 调用方读);**错误写 stderr 并返回退出码 1**(任何调用方都能从 stderr 看到,UI 会弹错误框)。按"参数是否需要用户每次改"二选一:不要给纯 CLI 插件硬做界面,也不要给需要用户传参的插件漏掉 GUI——UI 调用方不会替用户传参。

GUI 插件从模板起步:复制本技能 `assets/plugin_template.py` 为新 main.py 再改。核心逻辑写成独立函数(如 `do_work()`),GUI 与 CLI 共用一份,不要写两遍。

### 3. 依赖

只用标准库最省事。需要第三方库:

```bash
python -m pip install <包名>
```

装完同步把 `包名==版本` 追加到 `~/.osisai/plugins/requirements.txt`(一行一个,与现有条目风格一致)。

### 4. 生成 icon.png

用户对图标没特别要求时,直接调 icon 插件 CLI 生成:以插件**中文名的第一个字**为文字——

```bash
python ~/.osisai/plugins/icon/main.py \
  --text <中文名第一个字> --shape <图形> --bg <背景色> --shape-color <图形色> \
  --text-color <文字色> --size 512 --out ~/.osisai/plugins/<英文名>/icon.png
```

颜色写法 `4287f5` / `#4287f5` / `red` 均可;`--bg` 省略为透明;图形可选 circle/squircle/square/triangle/star/heart/diamond/plus。

**配色铁则**:渲染时文字画在图形正上方、图形画在背景上,三个颜色必须两两可区分,尤其文字色与图形色要强对比。用下表配方,按 plugins.json 里已有插件数对 8 取模选行——新插件之间天然错开,不必与现有图标逐一比对:

| # | bg | shape-color | text-color | shape 备选 |
|---|------|--------|--------|---------------------|
| 0 | 4287f5 | ffffff | 1a2b4c | circle / squircle |
| 1 | f5a142 | 3a2c14 | ffffff | squircle / diamond |
| 2 | 42a85c | ffffff | 16351f | circle / plus |
| 3 | 9b59b6 | ffffff | 2c1a3a | star / circle |
| 4 | e74c3c | ffffff | 3a1210 | heart / square |
| 5 | 16a085 | ffffff | 0e3f38 | triangle / circle |
| 6 | 2c3e50 | ffffff | e67e22 | squircle / star |
| 7 | d35400 | ffffff | 331a05 | diamond / square |

### 5. 注册 plugins.json

用本技能自带的注册脚本,**不要**用 `python -c` 内联改 JSON——中文与 Windows 反斜杠路径在 bash/GBK 控制台下会转义报错:

```bash
python <skill_dir>/scripts/register_plugin.py add \
  --name '单位换算器' --dir unitconv \
  --desc '单位换算:长度与温度单位互转' \
  --detail 'GUI:选类别与单位,输数值点转换。命令行:...\unitconv\main.py 100 m mm 输出 100000'
```

脚本自动生成 `icon`(`<dir>/icon.png`)与 `cmd`(`<dir>/main.py`)字段,以 UTF-8 写回并自校验 JSON 合法性;重复注册会报错,改插件后重新注册加 `--replace`(原地替换,不打乱列表顺序)。`detail` 要亲自写好:GUI 用法 + CLI 实际命令与示例,命令里用 `...` 代指插件绝对路径前缀,风格对齐现有条目。

### 6. 验证(完工前必做)

- CLI 真跑一遍:核对 stdout 输出(给 CLI 调用方读)与退出码
- **错误路径确认写 stderr 且返回非零**(任何调用方 + UI 都看得到)
- 纯 CLI 插件:实测 `python main.py --ui` 等于按默认参数执行;若会走"用法提示"分支,确认提示进了 stderr(UI 弹框靠它)
- GUI 插件:在能开 GUI 的环境实测 `--ui`,窗口里能看见结果;**不需要**走 stderr
- GUI 做静态检查即可(无显示环境):`python -m py_compile <main.py>`
- `python -m json.tool ~/.osisai/plugins/plugins.json` 通过
- icon.png 已生成且非空

### 7. 完工报告

列出:插件路径、GUI 用法、CLI 用法示例(真实可复制)、依赖变动(装了什么、requirements.txt 加了什么)、plugins.json 已注册。

## 修改 / 删除插件

- **改**:直接改 `~/.osisai/plugins/<英文名>/main.py`;用法变了就用 `register_plugin.py add --replace ...` 更新对应条目的 desc/detail
- **删**:删插件目录,再用 `register_plugin.py remove --dir <英文名>` 删掉条目

## 改官方 skill

用户说某 skill 不好用、规则错了、要改官方流程时,**不要**改安装包里的正文。

### 步骤

1. **确认 skill 名 `<name>`**(目录名,如 `osis-engine`)。不确定就先 `ls` 官方目录,不要猜。
2. **用户副本**`%USERPROFILE%\.osisai\.agents\skills\<name>\`:
   - **已存在**:这就是当前生效的整份替换层。只改这里。不要再从官方覆盖拷一遍(会冲掉用户已改内容),除非用户明确要求「用官方重新铺一份再改」。
   - **不存在**:把官方 `<name>` **整目录**复制到该路径(含 `SKILL.md`、`references/`、`scripts/`、`assets/`、`evals/` 等全部文件)。跳过源目录里的 `.git`(若有)。用 `Path.resolve()` 拷真实文件,不要拷成链接(改链接=改官方)。
3. **只改用户副本**。改完核对:用户目录是完整 skill,不是单文件。
4. 提醒用户:**下次会话**才加载用户覆盖层;本会话仍可能是官方那份。
5. 完工报告写明:官方源路径(只读)、用户副本路径、改了哪些文件、覆盖语义是整份替换。

复制骨架(把 `src` 换成已 resolve 的官方目录):

```python
from pathlib import Path
import shutil
name = "<name>"
src = Path(r"<official-dir>").resolve()
dst = Path.home() / ".osisai" / ".agents" / "skills" / name
if not src.joinpath("SKILL.md").is_file():
    raise SystemExit(f"官方 skill 不存在: {src}")
if dst.exists():
    raise SystemExit(f"用户副本已在,只改这里: {dst}")
dst.parent.mkdir(parents=True, exist_ok=True)
shutil.copytree(src, dst, ignore=lambda d, names: {".git"} if ".git" in names else set())
print(dst)
```

### 撤销覆盖

删掉 `%USERPROFILE%\.osisai\.agents\skills\<name>\` 整目录后,同名官方 skill 重新生效。不要删安装包里的官方目录。

## 模型入库

用户觉得当前桥建得好、希望以后基于它再改:把这份模型加入**该桥型 skill 的模板库**。复制到用户态,再加一个模板。不要只把 `.out` 丢进模板库;官方查库 `ls` 的是目录,复制的是 `prep`。不要写安装包。

### 步骤

1. **确认当前已打开的 OSIS 项目**;路由桥型 → 官方 skill 名(如 `osis-bridge-rigid-frame-box`)。不确定就 `ls` 官方/已加载的 bridge skills,不要猜。
2. **导出**:界面手建的模型可能还没进 `py/`。入库以现网模型为准时:
   ```bash
   python -c "from pyosis import OSISEngine; OSISEngine().sync_apdl(force_export=True)"
   ```
   把界面模型写进当前项目 `py/prep/`。失败则停,不要拿过期 py 入库。
3. **按 §改官方 skill**:用户态还没有该 `<name>` 就整目录复制到 `~/.osisai/.agents/skills/<name>/`(`Path.resolve()` 拷真实文件,不要拷成链接);已有用户副本只改副本。
4. **模板目录名**:参考该桥型现有命名(如 `变截面连续刚构-86+160+86-双肢`)。有画像用画像里的跨径/桥型拼;没有就请用户给短名。与已有目录同名须先问用户覆盖还是换名。
5. **拷产物**(必须与官方模板同构;不要只拷 `.out`;不要拷 `image/` `Check/` `Result/` `secmesh/` 等 OSIS 自动目录):
   ```
   <模板名>/
     项目画像.md
     prep/
       _0_engine.py … _10_stage.py
       main.py
   ```
   把当前项目的 `py/prep/`(及项目根 `项目画像.md`,有则拷)拷到用户 skill 副本 `references/templates/<目录名>/`。
6. 若该桥型 SKILL.md 里有「当前 N 个」硬编码名单,只在**用户副本**追加新目录名;查库仍以 `ls` 为准。
7. 提醒:下次会话才加载用户覆盖层。完工报告:桥型 skill、模板路径、是否新建了用户副本、`sync_apdl` 是否成功。

## 创建 skill

### 1. 建目录与文件

**只**写 `~/.osisai/.agents/skills/<英文名>/SKILL.md`。命名小写 kebab-case,如 `osis-bridge-arch-special`。不要写安装包里的官方 skill。

若新名字与官方同名,这不是「旁边再放一份」,而是**整份替换官方**。用户没说要覆盖官方时,换一个不冲突的名字;用户就是要改官方,走 §改官方 skill。

### 2. SKILL.md 格式

```markdown
---
name: <与目录同名>
description: >
  <干什么 + 什么情况下必须触发。写得主动些:把用户可能的说法列进去,
  如"建拱桥""异形拱",让 AI 一看 description 就知道何时该加载它。>
---

# <skill 名>

<正文>
```

### 3. 正文只写增量知识

skill 是给 AI 的操作手册,价值全在"AI 自己想不到、查不到的领域知识":

- 决策规则与流程步骤(先做什么后做什么、什么情况走哪条路)
- 路径、契约、参数表、组名等硬约定
- 已知坑与失败模式(以前怎么错的、怎么绕)
- 可直接复制执行的命令 / 代码骨架

不写通用编程常识与套话。超过约 300 行就把大块参考(长参数表、模板代码)拆到同目录 `references/*.md`,正文里指路什么时候去读。检验标准:AI 加载后照着做就能做对,不需要再猜。

领域细节拿不准时不要停下来逐项反问:先按通用知识写初版,不确定的默认值/参数留 `<!-- TODO: 想要什么 -->`,在完工报告里列出这些假设请用户纠正。

### 4. 验证

- frontmatter 用命令验证(打印出 dict 且 name/description 齐全即通过):
  ```bash
  python -c "import yaml,io;print(yaml.safe_load(io.open(r'<SKILL.md路径>',encoding='utf-8').read().split('---')[1]))"
  ```
- description 覆盖用户的典型触发说法;正文里出现的命令真实可跑
- 提醒用户:新 skill / 用户覆盖层从**下次会话**开始生效,本会话不会自动加载

### 5. 完工报告

列出:skill 路径(必须在 `~/.osisai/.agents\skills\`),触发场景(用户说什么会命中),是否覆盖了同名官方(整份替换),内容结构,验证结果。

## 修改 / 删除用户 skill

- **改用户自己建的 skill**:直接改 `~/.osisai/.agents/skills/<name>/`
- **改官方 skill**: 参考 §改官方 skill,禁止改安装包
- **删用户 skill / 撤销覆盖**:删用户目录整份;官方同名(若有)会重新露出来。批量删除先列清单让用户确认

## 通用守则

- 插件代码不硬编码敏感信息;文件操作只动用户明确指定的路径,以及本技能规定的 `~/.osisai` 下插件/skill/memory
- 批量删除/覆盖类操作必须先列清单让用户确认,或提供 `--dry-run`
- 改完必跑对应验证,禁止"写完就说完成"
- **禁止**为了「修不好用」而改安装包官方 skill;更新会清掉
