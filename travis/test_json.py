"""
Travis Test file:
Test JSON files for errors.
"""

import json
from collections import OrderedDict
from pathlib import Path


def pytest_generate_tests(metafunc):
    if 'json_file' in metafunc.fixturenames:
        paths = list(Path().rglob("*.json"))
        metafunc.parametrize('json_file', paths, ids=list(map(str, paths)))


def test_json(json_file):
    with json_file.open(encoding="utf-8") as f:
        text = f.read()

    data = json.loads(text, object_pairs_hook=OrderedDict)
    formatted_text = json.dumps(data, indent=4) + '\n'
    assert formatted_text == text, "Improperly formatted JSON file"
