"""
Travis Test file:
Test JSON files for errors.
"""

import codecs
import fnmatch
import json
import os
import sys
from collections import OrderedDict

error = False
warning = False
print("Travis: Testing all JSON files in source")

for root, dirs, files in os.walk('.'):
    for filename in fnmatch.filter(files, '*.json'):
        file = os.path.join(root, filename)
        with codecs.open(file, encoding="utf-8") as f:
            text = f.read()

        try:
            data = json.loads(text, object_pairs_hook=OrderedDict)
        except Exception as e:
            error = True
            print("Travis: {} is not a valid JSON file, json.load threw exception:\n{}".format(file, e))
        else:
            formatted_text = json.dumps(data, indent=4) + '\n'

            if text != formatted_text:
                print("Travis: {} is not a properly formatted JSON file".format(file))
                warning = True

if error:
    sys.exit(1)

if warning:
    sys.exit(2)
