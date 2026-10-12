"""Observable artifact, budget, and safe-write checks; not LLM behavior tests."""

import copy
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills' / 'sidequest' / 'scripts' / 'build_personal_skill.py'
spec = importlib.util.spec_from_file_location('builder', SCRIPT)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class BuilderTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads((ROOT / 'examples' / 'slow-living-plan.json').read_text(encoding='utf-8'))

    def test_standalone_artifact_contains_selected_personalization(self):
        with tempfile.TemporaryDirectory() as directory:
            target = builder.build(self.plan, directory)
            actual = {p.relative_to(target).as_posix() for p in target.rglob('*') if p.is_file()}
            self.assertEqual(actual, {'SKILL.md', 'profile.md', 'progress.md',
                                      'references/companion.md', 'references/delivery.md',
                                      'agents/openai.yaml'})
            # Every entrypoint reference resolves inside the generated skill, not the source repo.
            entrypoint = (target / 'SKILL.md').read_text(encoding='utf-8')
            for link in re.findall(r'\]\(([^)]+)\)', entrypoint):
                self.assertTrue((target / link).is_file(), link)
            self.assertNotIn('{{', entrypoint)
            self.assertIn(self.plan['name'], entrypoint)
            self.assertIn(self.plan['display_name'], entrypoint)
            profile = (target / 'profile.md').read_text(encoding='utf-8')
            for quest in self.plan['quests']:
                for field in ('title', 'why', 'baseline', 'goal', 'first_step'):
                    self.assertIn(quest[field], profile)
            self.assertIn('45', profile)
            for path in target.rglob('*'):
                if path.is_file():
                    self.assertNotIn(str(ROOT), path.read_text(encoding='utf-8'))

    def test_unconfirmed_plan_produces_no_output(self):
        for value in (False, 1, 'true', None):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                self.plan['confirmed'] = value
                with self.assertRaises(ValueError):
                    builder.build(self.plan, directory)
                self.assertEqual(list(Path(directory).iterdir()), [])

    def test_shared_budget_rejects_overallocation(self):
        self.plan['quests'][1]['sessions_per_week'] = 2
        with self.assertRaises(ValueError):
            builder.validate_plan(self.plan)

    def test_low_energy_cannot_be_more_work(self):
        self.plan['rhythm']['low_energy_minutes'] = 16
        with self.assertRaises(ValueError):
            builder.validate_plan(self.plan)

    def test_five_minutes_weekly_and_rest_are_valid(self):
        self.plan['quests'] = [self.plan['quests'][0]]
        self.plan['quests'][0]['sessions_per_week'] = 1
        self.plan['rhythm'].update(minutes_per_session=5, sessions_per_week=1, low_energy_minutes=0)
        builder.validate_plan(self.plan)

    def test_session_only_preference_survives_generation(self):
        self.plan['profile']['memory'] = 'session-only'
        with tempfile.TemporaryDirectory() as directory:
            target = builder.build(self.plan, directory)
            self.assertIn('session-only', (target / 'profile.md').read_text(encoding='utf-8'))
            # A new artifact must not contain invented finished lessons.
            self.assertNotIn(self.plan['quests'][0]['first_step'],
                             (target / 'progress.md').read_text(encoding='utf-8'))

    def test_existing_skill_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            target = builder.build(self.plan, directory)
            before = {p.relative_to(target): p.read_bytes() for p in target.rglob('*') if p.is_file()}
            self.plan['profile']['tone'] = 'A later plan must not overwrite the original.'
            with self.assertRaises(FileExistsError):
                builder.build(self.plan, directory)
            after = {p.relative_to(target): p.read_bytes() for p in target.rglob('*') if p.is_file()}
            self.assertEqual(before, after)

    def test_existing_symlink_is_not_followed(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            outside = parent / 'other-personal-data'
            outside.mkdir()
            (parent / self.plan['name']).symlink_to(outside, target_is_directory=True)
            with self.assertRaises(FileExistsError):
                builder.build(self.plan, parent)
            self.assertEqual(list(outside.iterdir()), [])

    def test_names_cannot_escape_output_directory(self):
        for name in ('../escape', '/absolute', 'a/b', '.', 'a--b', 'A', 'x' * 64):
            with self.subTest(name=name):
                self.plan['name'] = name
                with self.assertRaises(ValueError):
                    builder.validate_plan(self.plan)

    def test_booleans_and_floats_are_not_time_budgets(self):
        for value in (True, 1.5, '10', -1, 0):
            with self.subTest(value=value):
                self.plan['rhythm']['minutes_per_session'] = value
                with self.assertRaises(ValueError):
                    builder.validate_plan(self.plan)

    def test_unknown_fields_and_duplicate_quests_rejected(self):
        with self.subTest('unknown field'):
            extra = copy.deepcopy(self.plan)
            extra['profile']['email'] = 'not-needed'
            with self.assertRaises(ValueError):
                builder.validate_plan(extra)
        with self.subTest('duplicate direction'):
            self.plan['quests'][1]['id'] = self.plan['quests'][0]['id']
            with self.assertRaises(ValueError):
                builder.validate_plan(self.plan)

    def test_cli_works_from_unrelated_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(SCRIPT), '--plan', str(ROOT / 'examples' / 'slow-living-plan.json'),
                 '--output', str(Path(directory) / 'output')],
                cwd=directory, text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((Path(directory) / 'output' / self.plan['name'] / 'SKILL.md').is_file())

    def test_yaml_like_names_remain_strings(self):
        # These are valid slugs but unquoted YAML would parse them as non-strings.
        for name in ('null', 'true', '123'):
            with self.subTest(name=name):
                self.plan['name'] = name
                entrypoint = builder.render_files(self.plan)['SKILL.md']
                serialized = entrypoint.splitlines()[1].removeprefix('name: ')
                self.assertEqual(json.loads(serialized), name)

    def test_every_public_plan_can_generate(self):
        for path in sorted((ROOT / 'examples').glob('*-plan.json')):
            with self.subTest(path=path.name), tempfile.TemporaryDirectory() as directory:
                plan = json.loads(path.read_text(encoding='utf-8'))
                target = builder.build(plan, directory)
                self.assertTrue((target / 'references' / 'delivery.md').is_file())

    def test_invalid_cli_input_leaves_no_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'invalid.json'
            source.write_text('{broken json', encoding='utf-8')
            output = Path(directory) / 'output'
            result = subprocess.run([sys.executable, str(SCRIPT), '--plan', str(source),
                                     '--output', str(output)], text=True, capture_output=True)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
