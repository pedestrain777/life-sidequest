# 安装、试用与更新

Life SideQuest 是一个 Skill 文件夹，不是独立 App。需要一个能读取 Skill 指令的 AI 助手；写文件、持久记录、联网和定时投递取决于宿主的实际能力。

## 路线一：让助手安装

在带有 Skill 安装能力的助手中说：

```text
请从 https://github.com/pedestrain777/life-sidequest 安装 skills/sidequest。
请安装整个目录，并确认入口、references、assets、scripts 都在。
如果已安装，不要覆盖我的个人 Skill 或进度，先说明更新范围。
```

安装完成后，在技能列表确认能找到「人生支线」；若未刷新，重启宿主再检查。Codex CLI / IDE 中可以用 `$sidequest`，其他界面按其技能选择器操作。当前目录和调用方式以 [OpenAI 官方 Skill 文档](https://learn.chatgpt.com/docs/build-skills) 为准。

```text
$sidequest 我的人生好像只剩主线了。
先和我聊聊兴趣和时间，方向确认后再为我生成个人 Skill。
```

本项目尚不声明其他宿主已经完成兼容性测试；能识别 `SKILL.md` 不等于有后台运行、邮箱访问或持久记忆。

## 路线二：手动安装到 Codex 本地目录

先克隆仓库，或在 GitHub 选择 Code → Download ZIP 后解压。

```bash
git clone https://github.com/pedestrain777/life-sidequest.git
cd life-sidequest
```

将 `skills/sidequest` **整个文件夹**放进用户目录 `.agents/skills/`，最终应是 `.agents/skills/sidequest/SKILL.md`，而不是多套一层 `skills`。

macOS / Linux，可在仓库根目录运行以下命令。它遇到同名目录或符号链接会停止，不合并覆盖：

```bash
mkdir -p "$HOME/.agents/skills"
if [ -e "$HOME/.agents/skills/sidequest" ] || [ -L "$HOME/.agents/skills/sidequest" ]; then
  printf '%s\n' 'sidequest 已存在，请先比较版本并备份，不直接覆盖。'
else
  cp -R skills/sidequest "$HOME/.agents/skills/sidequest"
fi
```

Windows PowerShell，同样在仓库根目录运行：

```powershell
$skillParent = Join-Path $env:USERPROFILE '.agents/skills'
$skillTarget = Join-Path $skillParent 'sidequest'
if (Test-Path -LiteralPath $skillTarget) {
  throw 'sidequest 已存在，请先比较版本并备份。'
}
New-Item -ItemType Directory -Force -Path $skillParent | Out-Null
Copy-Item -LiteralPath 'skills/sidequest' -Destination $skillTarget -Recurse
```

选择一个安装位置即可，不要把同名 Skill 同时放进多个被扫描目录。如果宿主版本使用其他技能路径，按该版本的安装工具或官方文档操作，不批量修改全局设置。

## 先看结果，不先做访谈

[完整生成示例](../examples/generated/sidequest-slow-living/SKILL.md) 可直接阅读。它来自明确标注的虚构输入，不是作者的个人画像。

有 Python 3.9+ 时也可在仓库根目录复现，不需要第三方 Python 包：

```bash
python3 skills/sidequest/scripts/build_personal_skill.py \
  --plan examples/slow-living-plan.json \
  --output .sidequest/private-skills
```

Windows 若命令名是 `py`，将 `python3` 替换为 `py -3`。另一份 [表达支线输入](../examples/storytelling-plan.json) 使用 `session-only` 模式：生成最小确认方案，但不追加练习进度。

脚本只把确认方案转成文件，不调用模型，不替用户做访谈，也不建立自动化。`confirmed: true` 只是数据标志，真实方案仍须先获得用户确认。

## 用自己的个人 Skill 继续

对话中确认方案后，助手会生成包含 `profile.md`、`progress.md` 和陪伴规则的独立目录。默认在 `.sidequest/private-skills/<name>/`；**生成不等于安装**。

让助手把该完整目录安装到宿主的私人技能位置，或明确告诉助手本地路径。之后可以这样调用：

```text
$sidequest-slow-living 今天有点累，按我的低精力方案来。
```

不要同时维护多份不同进度的副本。安装后以实际被读取的那份个人目录为准，后续在原位调整。更新生成器不会自动更新或覆盖已经生成的个人 Skill。

## 常见问题

| 现象 | 检查方式 |
| --- | --- |
| 找不到 Skill | 检查完整目录、`SKILL.md` 所在层级、宿主的扫描路径和技能列表；必要时重启 |
| 能读入口但找不到模板 | 重新取得整个 `skills/sidequest` 目录，不只下载单个 Markdown |
| 运行示例提示目标已存在 | 是防覆盖机制；先查看原结果，另选新的输出父目录试用，不删除私人记录 |
| 没有 Python | 让具备文件工具的助手按模板生成；只有文本聊天时提供可复制内容 |
| 忘了上次内容 | 确认宿主读到了同一份个人目录，且你允许本地记录；不会自动读取其他聊天 |
| 没收到每日邮件 | 安装 Skill 不会开通邮件；按 [定时与邮件指南](automation.md) 检查两种能力 |

更新前保留你修改过的文件，比较新版差异。项目不会自行上传你的个人目录。提交 Issue 时只贴脱敏后的错误和最小复现步骤。
