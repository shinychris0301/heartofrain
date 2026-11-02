import json
import sys
import uuid
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from hotr_backend.api import create_app

database = root.parent / '.verification-cache/Backend' / ('Schema-' + uuid.uuid4().hex) / 'authority.sqlite3'
schema = create_app(database).openapi()
output = root.parent / 'Verification/Evidence/Backend/OpenAPI.json'
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(schema, indent=2) + '\n', encoding='utf-8')
print('Exported credential-free OpenAPI contract.')
