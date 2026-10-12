#!/usr/bin/env python3
"""Build a self-contained personal skill from an explicitly confirmed plan.

Python 3.9+, standard library only. No network, scheduler, or host configuration.
The caller is responsible for obtaining real user confirmation and choosing a
private output location. The confirmation flag is not an authorization system.
"""

import argparse
import json
from pathlib import Path
import re
import sys


SKILL_ROOT = Path(__file__).resolve().parents[1]


def require_object(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError(f"{label}: expected exactly these fields: {', '.join(keys)}")


def require_text(value, label, single_line=False):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}: expected non-empty text")
    if single_line and any(c in value for c in '\r\n'):
        raise ValueError(f"{label}: expected a single line")


def require_slug(value, label):
    if (not isinstance(value, str) or len(value) > 63
            or re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', value) is None):
        raise ValueError(f"{label}: use 1–63 lowercase letters/digits with single hyphens")


def require_integer(value, label, minimum=1):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{label}: expected an integer >= {minimum}")


def require_text_list(value, label, allow_empty=False):
    if not isinstance(value, list) or (not value and not allow_empty):
        raise ValueError(f"{label}: expected a list of text values")
    for item in value:
        require_text(item, label)


def validate_plan(plan):
    require_object(plan, ('name', 'display_name', 'confirmed', 'profile', 'rhythm', 'quests'), 'plan')
    require_slug(plan['name'], 'name')
    require_text(plan['display_name'], 'display_name', single_line=True)
    if plan['confirmed'] is not True:
        raise ValueError('confirmed: the user must confirm the plan before building')

    profile = plan['profile']
    require_object(profile, ('main_quest', 'motivation', 'interests', 'boundaries',
                             'learning_style', 'tone', 'language', 'memory'), 'profile')
    for key in ('main_quest', 'motivation', 'learning_style', 'tone', 'language'):
        require_text(profile[key], f'profile.{key}')
    require_text_list(profile['interests'], 'profile.interests')
    require_text_list(profile['boundaries'], 'profile.boundaries', allow_empty=True)
    if profile['memory'] not in ('local', 'session-only'):
        raise ValueError('profile.memory: choose local or session-only')

    rhythm = plan['rhythm']
    require_object(rhythm, ('minutes_per_session', 'sessions_per_week',
                            'low_energy_minutes', 'review_every_sessions'), 'rhythm')
    for key in ('minutes_per_session', 'sessions_per_week', 'review_every_sessions'):
        require_integer(rhythm[key], f'rhythm.{key}')
    require_integer(rhythm['low_energy_minutes'], 'rhythm.low_energy_minutes', minimum=0)
    if rhythm['low_energy_minutes'] > rhythm['minutes_per_session']:
        raise ValueError('low-energy time cannot exceed the normal session budget')

    quests = plan['quests']
    if not isinstance(quests, list) or not quests:
        raise ValueError('quests: choose at least one confirmed direction')
    identifiers = set()
    for quest in quests:
        require_object(quest, ('id', 'title', 'why', 'baseline', 'goal',
                               'sessions_per_week', 'first_step', 'steps'), 'quest')
        require_slug(quest['id'], 'quest.id')
        if quest['id'] in identifiers:
            raise ValueError('quest.id: duplicate identifiers are not allowed')
        identifiers.add(quest['id'])
        for key in ('title', 'why', 'baseline', 'goal', 'first_step'):
            require_text(quest[key], f'quest.{key}')
        require_integer(quest['sessions_per_week'], 'quest.sessions_per_week')
        require_text_list(quest['steps'], 'quest.steps')
    if sum(q['sessions_per_week'] for q in quests) > rhythm['sessions_per_week']:
        raise ValueError('quest allocations exceed the shared weekly session budget')


def bullet_list(values):
    return '\n'.join('- ' + value.replace('\n', '\n  ') for value in values) or '- 暂无额外约定。'


def render_profile(plan):
    profile, rhythm = plan['profile'], plan['rhythm']
    allocated = sum(q['sessions_per_week'] for q in plan['quests'])
    memory = ('local（同意在本地保存精简学习反馈）' if profile['memory'] == 'local'
              else 'session-only（只在当前对话保持进度，不追加持久化学习记录）')
    sections = [
        '# 我的支线方案\n\n以下是用户确认后的摘要；不是能力诊断，也不是自动化授权。',
        '## 现在的我\n\n'
        f"主线：{profile['main_quest']}\n\n"
        f"为什么开支线：{profile['motivation']}\n\n"
        f"表达过的兴趣：\n{bullet_list(profile['interests'])}",
        '## 怎样陪我\n\n'
        f"内容与互动偏好：{profile['learning_style']}\n\n"
        f"语气：{profile['tone']}\n\n输出语言：{profile['language']}\n\n"
        f"记录方式：{memory}\n\n不希望发生：\n{bullet_list(profile['boundaries'])}",
        '## 共享预算\n\n'
        f"- 每次最多 {rhythm['minutes_per_session']} 分钟，每周共 {rhythm['sessions_per_week']} 次。\n"
        f"- 每周总时间上限：{rhythm['minutes_per_session'] * rhythm['sessions_per_week']} 分钟。\n"
        f"- 已分配 {allocated} 次；未分配的次数不强制填满。\n"
        f"- 低精力版本：{rhythm['low_energy_minutes']} 分钟；0 分钟表示休息。\n"
        f"- 在有用户反馈的 {rhythm['review_every_sessions']} 次体验后提议轻量复盘。\n"
        '- 阅读、准备、思考与动手共享上述时间；各方向不能各自再领一份预算。\n'
        '- 自动提醒：未配置。此频率只约定内容节奏，不创建后台任务。',
    ]
    for quest in plan['quests']:
        sections.append(
            f"## 支线：{quest['title']}\n\n"
            f"标识：{quest['id']}\n\n为什么适合我：{quest['why']}\n\n"
            f"当前起点：{quest['baseline']}\n\n想看到的变化：{quest['goal']}\n\n"
            f"每周分配：{quest['sessions_per_week']} 次。\n\n"
            f"第一步：{quest['first_step']}\n\n后续可调整的小台阶：\n{bullet_list(quest['steps'])}"
        )
    return '\n\n'.join(sections) + '\n'


def render_files(plan, skill_root=SKILL_ROOT):
    validate_plan(plan)
    entrypoint = (skill_root / 'assets' / 'personal-skill.md').read_text(encoding='utf-8')
    entrypoint = entrypoint.replace('{{name}}', plan['name']).replace('{{display_name}}', plan['display_name'])
    companion = (skill_root / 'assets' / 'companion.md').read_text(encoding='utf-8')
    delivery = (skill_root / 'assets' / 'delivery.md').read_text(encoding='utf-8')
    quote = lambda value: json.dumps(value, ensure_ascii=False)
    ui = (
        'interface:\n'
        f"  display_name: {quote(plan['display_name'])}\n"
        '  short_description: "按已确认的兴趣、起点和共享时间预算，持续陪伴并调整你自己的生活支线"\n'
        f"  default_prompt: {quote('用 $' + plan['name'] + ' 按我的个人方案继续一次轻量支线体验，先参考已有反馈。')}\n"
        'policy:\n  allow_implicit_invocation: true\n'
    )
    progress = (
        '# 支线进度\n\n'
        '初始状态：尚无体验或学习完成记录。\n\n'
        '先查看 profile.md 的记录方式。session-only 模式下不追加本文件。\n'
        'local 模式只追加精简摘要，区分已提供内容与用户反馈已读、理解、已尝试；未知保持未知。\n'
    )
    return {
        'SKILL.md': entrypoint,
        'profile.md': render_profile(plan),
        'progress.md': progress,
        'references/companion.md': companion,
        'references/delivery.md': delivery,
        'agents/openai.yaml': ui,
    }


def build(plan, output, skill_root=SKILL_ROOT):
    # Validate and render before creating any files. A failed validation leaves no output.
    files = render_files(plan, skill_root)
    target = Path(output).expanduser() / plan['name']
    target.parent.mkdir(parents=True, exist_ok=True)
    # Never merge into or overwrite an existing personal skill, including a symlink.
    target.mkdir(mode=0o700, exist_ok=False)
    for relative, content in files.items():
        path = target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('x', encoding='utf-8') as stream:
            stream.write(content)
    return target.resolve()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True, type=Path, help='Local JSON containing the confirmed minimal plan')
    parser.add_argument('--output', required=True, type=Path, help='Private parent directory for the generated skill')
    args = parser.parse_args()
    try:
        with args.plan.open(encoding='utf-8') as stream:
            plan = json.load(stream)
        target = build(plan, args.output)
    except (ValueError, OSError) as exc:
        print(f'Build failed: {exc}', file=sys.stderr)
        return 1
    print(f'Created personal skill: {target}')
    print('Files only: not installed, not published, no reminders configured.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
