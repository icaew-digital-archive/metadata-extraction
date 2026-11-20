"""
Tests for the metadata extraction tool. No network access or API keys needed.

Run from the project folder with:
    venv/bin/python -m unittest discover tests
"""

import json
import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
from json_metadata_writer import JSONMetadataWriter  # noqa: E402
from metadata_extractor import MetadataExtractor  # noqa: E402
from openai_client import OpenAIClient, strip_code_fences  # noqa: E402
import main  # noqa: E402
import preservica_writer as pw  # noqa: E402

PROFILES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'profiles')
ICAEW = os.path.join(PROFILES, 'icaew.yaml')
DEFAULT = os.path.join(PROFILES, 'default.yaml')


class TestSystemPrompt(unittest.TestCase):
    def test_profiles_build(self):
        for path in (ICAEW, DEFAULT):
            for subjects in (True, False):
                prompt = config.get_system_prompt(subjects, path)
                self.assertIn('### Output Format', prompt)
                self.assertIn('"Title"', prompt)
                self.assertIn('JSON', prompt)  # required by JSON output mode
                self.assertNotIn('[Warning: could not load topic list', prompt)

    def test_no_subjects_omits_topic_list(self):
        self.assertIn('Topic List for Subject Classification', config.get_system_prompt(True, ICAEW))
        prompt = config.get_system_prompt(False, ICAEW)
        self.assertNotIn('Topic List for Subject Classification', prompt)
        self.assertIn('**Subject (RESERVED)**', prompt)

    def test_list_profiles(self):
        paths = [p for _, p in config.list_profiles()]
        self.assertIn(ICAEW, paths)
        self.assertIn(DEFAULT, paths)


    def test_rules_are_stated_once(self):
        prompt = config.get_system_prompt(True, ICAEW)
        for phrase in ('British English spelling', 'ICAEW reference codes', 'contextual background',
                       'straight quotes', 'Acronyms must ALWAYS'):
            self.assertEqual(prompt.count(phrase), 1, phrase)
        self.assertIn('"OECD" (not "Oecd")', prompt)
        self.assertNotIn('Briefly summarise', prompt)
        default = config.get_system_prompt(True, DEFAULT)
        self.assertIn('"UK" (not "Uk")', default)
        self.assertNotIn('{acronym_examples}', default)

    def test_date_rule_uses_uk_order(self):
        prompt = config.get_system_prompt(True, ICAEW)
        self.assertIn('"10/7/2009" means 10 July 2009 and becomes "2009-07-10"', prompt)
        self.assertNotIn('"2009-10-07"', prompt)
        self.assertNotIn('clearly American', prompt)


class TestSubjectValidation(unittest.TestCase):
    def test_icaew_topics_loaded(self):
        topics, max_count = config.get_subject_constraints(ICAEW)
        self.assertGreater(len(topics), 100)
        self.assertGreater(max_count, 0)

    def test_filters_unknown_and_truncates(self):
        valid = {'A', 'B', 'C'}
        self.assertEqual(config.validate_subjects(['A', 'X', 'B', 'C'], valid, 2), ['A', 'B'])

    def test_no_constraints(self):
        self.assertEqual(config.validate_subjects(['X', 'Y'], set(), 0), ['X', 'Y'])


class TestTextCleaning(unittest.TestCase):
    def setUp(self):
        self.w = JSONMetadataWriter.__new__(JSONMetadataWriter)

    def test_all_fields(self):
        cases = {
            'ICAEW’s report': "ICAEW's report",
            '“Quoted”': '"Quoted"',
            'Cost £5m': 'Cost £5m',             # pound sign kept
            'Café society': 'Café society',     # accents kept
            'Wait…': 'Wait...',
            '  padded  ': 'padded',
            '': '',
            # Dashes are left alone outside titles
            'Wanted urgently — the T-shaped FD': 'Wanted urgently — the T-shaped FD',
            'Pages 3–5': 'Pages 3–5',
            'A â€” B': 'A — B',  # mojibake repaired, not converted
        }
        for raw, expected in cases.items():
            self.assertEqual(self.w._clean_text(raw), expected, raw)

    def test_titles(self):
        cases = {
            'Title — subtitle': 'Title: subtitle',
            'Title–subtitle': 'Title: subtitle',
            'Annual report 2008–09': 'Annual report 2008-09',
            'Title â€” sub': 'Title: sub',  # mojibake em dash
            'ICAEW’s review': "ICAEW's review",
        }
        for raw, expected in cases.items():
            self.assertEqual(self.w._clean_text(raw, title=True), expected, raw)

    def test_lists_are_cleaned(self):
        self.assertEqual(self.w._clean_value(['O’Brien ', 1]), ["O'Brien", 1])


class TestJSONWriter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, 'out.json')

    def tearDown(self):
        self.tmp.cleanup()

    def test_write_and_read_back(self):
        w = JSONMetadataWriter(self.path, ICAEW)
        w.write_metadata(json.dumps({'Title': 'A — b', 'Description': 'A — b.',
                                     'Creator': ['ICAEW’s team'],
                                     'icaew:Notes': 'AI note', 'Rights': 'x'}),
                         '/x/doc.pdf', 'docx')
        records = JSONMetadataWriter(self.path, ICAEW).get_records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['asset_id'], 'doc.pdf')
        self.assertEqual(records[0]['original_format'], 'docx')
        self.assertNotIn('model', records[0])
        self.assertEqual(records[0]['metadata']['Title'], 'A: b')
        self.assertEqual(records[0]['metadata']['Description'], 'A — b.')
        self.assertEqual(records[0]['metadata']['Creator'], ["ICAEW's team"])
        # Reserved fields are never filled by the AI
        self.assertEqual(records[0]['metadata']['icaew:Notes'], '')
        self.assertEqual(records[0]['metadata']['Rights'], '')
        self.assertEqual(w.get_record_count(), 1)
        leftovers = [f for f in os.listdir(self.tmp.name) if f.startswith('.tmp_')]
        self.assertEqual(leftovers, [])

    def test_corrupt_file_is_not_overwritten(self):
        damaged = '{"metadata": [{"asset_id": "keep-me"'
        with open(self.path, 'w') as f:
            f.write(damaged)
        with self.assertRaises(ValueError):
            JSONMetadataWriter(self.path, ICAEW)
        with open(self.path) as f:
            self.assertEqual(f.read(), damaged)

    def test_invalid_metadata_leaves_file_unchanged(self):
        w = JSONMetadataWriter(self.path, ICAEW)
        with open(self.path) as f:
            before = f.read()
        with self.assertRaises(ValueError):
            w.write_metadata('not json', '/x/doc.pdf')
        with open(self.path) as f:
            self.assertEqual(f.read(), before)


def topic_parents():
    """Map each topic in the ICAEW topic list to its list of ancestor topics."""
    parents, stack = {}, []
    with open(os.path.join(PROFILES, 'topic_list.txt'), encoding='utf-8') as f:
        for line in f:
            stripped = line.strip()
            if not stripped.startswith('- '):
                continue
            depth = (len(line) - len(line.lstrip())) // 2
            stack = stack[:depth]
            parents[stripped[2:]] = list(stack)
            stack.append(stripped[2:])
    return parents


def assert_valid_subject_path(test, subjects):
    """Every subject must exist, and every subject's parent topics must also be listed."""
    parents = topic_parents()
    for subject in subjects:
        test.assertIn(subject, parents, f'{subject!r} is not in topic_list.txt')
        for ancestor in parents[subject]:
            test.assertIn(ancestor, subjects, f'{subject!r} is missing its parent {ancestor!r}')


class TestSubjectExamples(unittest.TestCase):
    def test_prompt_subject_examples_match_topic_list(self):
        prompt = config.get_system_prompt(True, ICAEW)
        section = prompt[prompt.index('**Subject (OPTIONAL)**'):prompt.index('**Source, Coverage, Rights')]
        examples = [json.loads(m) for m in __import__('re').findall(r'\[".*?"\]', section)]
        self.assertGreaterEqual(len(examples), 3)
        for subjects in examples:
            assert_valid_subject_path(self, subjects)

    def test_profile_example_subjects_include_parents(self):
        import yaml
        with open(ICAEW, encoding='utf-8') as f:
            profile = yaml.safe_load(f)
        for ex in profile['examples']:
            assert_valid_subject_path(self, json.loads(ex)['Subject'])


class TestICAEWProfile(unittest.TestCase):
    def test_notes_is_reserved(self):
        self.assertIn('icaew:Notes', config.get_reserved_fields(ICAEW))
        prompt = config.get_system_prompt(True, ICAEW)
        self.assertIn('**icaew:Notes (RESERVED)**\n- This field is entered by staff, never by the AI', prompt)
        # Other reserved fields keep the default wording
        self.assertIn('**icaew:InternalReference (RESERVED)**\n- This field is reserved for future use', prompt)

    def test_examples_follow_own_rules(self):
        import yaml
        with open(ICAEW, encoding='utf-8') as f:
            profile = yaml.safe_load(f)
        topics, max_count = config.get_subject_constraints(ICAEW)
        for ex in profile['examples']:
            d = json.loads(ex)
            self.assertEqual(d['entity.title'], d['Title'])
            self.assertEqual(d['entity.description'], d['Description'])
            self.assertTrue(d['Subject'], 'examples should show real subjects')
            self.assertLessEqual(len(d['Subject']), max_count)
            for subject in d['Subject']:
                self.assertIn(subject, topics)
            self.assertEqual(d['icaew:Notes'], '')


class TestStripCodeFences(unittest.TestCase):
    def test_variants(self):
        self.assertEqual(strip_code_fences('{"a": 1}'), '{"a": 1}')
        self.assertEqual(strip_code_fences('```json\n{"a": 1}\n```'), '{"a": 1}')
        self.assertEqual(strip_code_fences('```json\n{"a": 1}\n```\n'), '{"a": 1}')
        self.assertEqual(strip_code_fences('```\n{"a": 1}'), '{"a": 1}')  # no closing fence


class FakeResponses:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=self.outputs.pop(0))


def make_client(outputs):
    client = OpenAIClient.__new__(OpenAIClient)
    client.model = 'test-model'
    client.system_prompt = 'Return JSON.'
    client.client = SimpleNamespace(responses=FakeResponses(outputs))
    return client


class TestOpenAIClient(unittest.TestCase):
    def test_returns_valid_json_and_requests_json_mode(self):
        c = make_client(['{"Title": "x"}'])
        self.assertEqual(c.extract_metadata('file-1'), '{"Title": "x"}')
        call = c.client.responses.calls[0]
        self.assertEqual(call['text'], {'format': {'type': 'json_object'}})
        self.assertEqual(call['model'], 'test-model')

    def test_retries_once_on_bad_json(self):
        c = make_client(['not json', '```json\n{"Title": "x"}\n```'])
        self.assertEqual(c.extract_metadata('file-1'), '{"Title": "x"}')
        self.assertEqual(len(c.client.responses.calls), 2)

    def test_gives_up_after_retries(self):
        c = make_client(['', '[1, 2]'])
        with self.assertRaises(ValueError):
            c.extract_metadata('file-1')


class FakeClient:
    def __init__(self, fail=False):
        self.fail = fail
        self.deleted = []

    def upload_file(self, path):
        return 'file-123'

    def extract_metadata(self, file_id, context_prompt=None):
        if self.fail:
            raise ValueError('boom')
        return '{}'

    def delete_file(self, file_id):
        self.deleted.append(file_id)


class TestMetadataExtractor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        self.tmp.close()

    def tearDown(self):
        os.unlink(self.tmp.name)

    def _extractor(self, fail):
        e = MetadataExtractor.__new__(MetadataExtractor)
        e.client = FakeClient(fail)
        return e

    def test_uploaded_file_deleted_on_success(self):
        e = self._extractor(False)
        e.extract_metadata(self.tmp.name)
        self.assertEqual(e.client.deleted, ['file-123'])

    def test_uploaded_file_deleted_on_failure(self):
        e = self._extractor(True)
        with self.assertRaises(ValueError):
            e.extract_metadata(self.tmp.name)
        self.assertEqual(e.client.deleted, ['file-123'])


class TestFormatDetection(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def _mapping(self, data):
        with open(os.path.join(self.dir, 'format_mapping.json'), 'w') as f:
            json.dump(data, f)
        return main.load_format_mapping(self.dir)

    def test_filename_keys(self):
        mapping = self._mapping({'a.pdf': 'docx'})
        self.assertEqual(main.detect_original_format(os.path.join(self.dir, 'a.pdf'), mapping), 'docx')

    def test_old_path_keys_with_different_spelling(self):
        # Older mapping files stored paths; "./dir/a.pdf" must match "dir/a.pdf"
        rel = os.path.relpath(self.dir)
        mapping = self._mapping({os.path.join(rel, 'a.pdf'): 'xlsx'})
        pdf = os.path.join('.', rel, 'a.pdf')
        self.assertEqual(main.detect_original_format(pdf, mapping), 'xlsx')

    def test_sibling_fallback_and_default(self):
        open(os.path.join(self.dir, 'b.pptx'), 'w').close()
        self.assertEqual(main.detect_original_format(os.path.join(self.dir, 'b.pdf'), {}), 'pptx')
        self.assertEqual(main.detect_original_format(os.path.join(self.dir, 'c.pdf'), {}), 'pdf')

    def test_pdf_files_sorted(self):
        for name in ('c.pdf', 'a.pdf', 'b.PDF', 'notes.txt'):
            open(os.path.join(self.dir, name), 'w').close()
        names = [os.path.basename(p) for p in main.get_pdf_files(folder_path=self.dir)]
        self.assertEqual(names, ['a.pdf', 'b.PDF', 'c.pdf'])

    def test_help_examples_use_valid_flags(self):
        epilog = main.create_parser().epilog
        self.assertNotIn('-f 3', epilog)


class TestPreservicaXML(unittest.TestCase):
    def test_asset_ref_from_filename(self):
        ref = 'cc56e888-8d18-5582-0d41-65c168d611ee'
        self.assertEqual(pw.asset_ref_from_filename(f'{ref}.pdf'), ref)
        self.assertIsNone(pw.asset_ref_from_filename('report.pdf'))

    def test_dc_xml(self):
        xml = pw.build_dc_xml({'Title': 'T', 'Creator': ['A', 'B', ''], 'Format': 'pdf'}, 'DOCX')
        root = ET.fromstring(xml)
        dc = '{%s}' % pw.DC
        self.assertEqual(root.find(dc + 'title').text, 'T')
        self.assertEqual([e.text for e in root.findall(dc + 'creator')], ['A', 'B'])
        self.assertEqual(root.find(dc + 'format').text, 'docx')

    def test_empty_metadata_gives_no_xml(self):
        self.assertIsNone(pw.build_dc_xml({'Title': '', 'Creator': []}))
        self.assertIsNone(pw.build_icaew_xml({'icaew:Notes': ''}))

    def test_existing_user_values(self):
        xml = pw.build_icaew_xml({'icaew:ContentType': 'Report', 'icaew:Notes': 'Checked by CM',
                                  'icaew:InternalReference': 'REF-1'})
        self.assertEqual(pw.existing_user_values(xml),
                         {'icaew:Notes': ['Checked by CM'], 'icaew:InternalReference': ['REF-1']})
        self.assertEqual(pw.existing_user_values(None), {})

    def test_overwrite_keeps_user_notes(self):
        old_xml = pw.build_icaew_xml({'icaew:ContentType': 'Article', 'icaew:Notes': 'Checked by CM'})
        written = {}

        class FakeAsset:
            metadata = {'u1': pw.ICAEW}
            title, description = 'T', 'D'

        class FakePreservica:
            def asset(self, ref):
                return FakeAsset()

            def metadata_for_entity(self, asset, schema):
                return old_xml if schema == pw.ICAEW else None

            def update_metadata(self, asset, schema, xml):
                written[schema] = xml
                return asset

            add_metadata = update_metadata

        record = {'asset_id': 'cc56e888-8d18-5582-0d41-65c168d611ee.pdf',
                  'metadata': {'Title': 'T', 'icaew:ContentType': 'Report', 'icaew:Notes': ''}}
        result = pw.apply_record(FakePreservica(), record, xip=False, overwrite=True)
        self.assertEqual(result['status'], 'applied', result)
        root = ET.fromstring(written[pw.ICAEW])
        ns = '{%s}' % pw.ICAEW
        self.assertEqual(root.find(ns + 'ContentType').text, 'Report')
        self.assertEqual(root.find(ns + 'Notes').text, 'Checked by CM')

    def test_icaew_xml_order(self):
        xml = pw.build_icaew_xml({'icaew:Notes': 'n', 'icaew:ContentType': 'Report', 'icaew:Extra': 'e'})
        tags = [el.tag.split('}')[1] for el in ET.fromstring(xml)]
        self.assertEqual(tags, ['ContentType', 'Notes', 'Extra'])


if __name__ == '__main__':
    unittest.main()
