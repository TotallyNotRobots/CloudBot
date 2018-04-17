import json
from collections import OrderedDict

import pytest


def pytest_collect_file(path, parent):
    if path.ext != ".json":
        return None

    return JsonItem(path, parent)


class JsonItem(pytest.Item, pytest.File):
    def runtest(self):
        with open(str(self.fspath), encoding='utf-8') as f:
            text = f.read()

        data = json.loads(text, object_pairs_hook=OrderedDict)
        formatted_text = json.dumps(data, indent=4) + '\n'
        assert formatted_text == text, "Improperly formatted JSON file"
