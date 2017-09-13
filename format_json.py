"""
Format all JSON files in the bot core in a consistent manor
"""

from pathlib import Path
import codecs
import json

path = Path().resolve()

for file in path.rglob("*.json"):
    with codecs.open(str(file), encoding='utf8') as f:
        data = json.load(f)

    with codecs.open(str(file), 'w', encoding='utf8') as f:
        print(json.dumps(data, indent=2), file=f)

