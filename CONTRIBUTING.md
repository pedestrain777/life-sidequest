# 参与 Life SideQuest

欢迎改进对话体验、安装说明、示例与生成器。先阅读 [核心 Skill](skills/sidequest/SKILL.md)：主题开放、用户确认、共享预算、真实反馈与最少记录，是项目的基本约定。

## 本地检查

Python 3.9+，无需第三方 Python 包：

```bash
python3 -m unittest discover -s tests -v
python3 scripts/package_release.py --output dist/life-sidequest.zip
```

自动测试验证生成文件、参数、引用和打包边界，不等于已经验证所有模型/宿主的对话效果。涉及对话规则的修改，用 [行为验收场景](tests/behavior-cases.md) 在实际可用环境试用，说明测了什么、没测什么。

修改模板或生成器后，用虚构方案重新生成 `examples/generated/sidequest-slow-living` 并比较变化；不要用自己的画像替换公开示例。脚本不覆盖已有目录，先生成到新临时目录，再有选择地更新示例文件。

## 提交范围

- 只提交开源包文件，不提交 `.sidequest`、个人 Skill、邮箱地址、密钥、邮件日志或私人聊天。
- 新增公开文件时同步 `release-manifest.json`。打包脚本只收录清单内的确切文件，不递归抓取整个工作区。
- 更新安装和能力说明时，区分已实现、依赖宿主、尚未接通；禁止用营销文案代替能力验证。
- 生成器的基本路径保持标准库可运行。不引入付费服务或额外网络访问作为默认步骤。
- 报告 Bug 时提供脱敏输入、运行环境和可复现步骤。发现凭据泄漏不要在公开 Issue 复制凭据；先撤销泄漏的凭据。

原始模板中的 `{{name}}` 和 `{{display_name}}` 是有意保留的变量；实际生成的入口不应再有未替换变量。
