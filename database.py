import os
from sqlalchemy import create_engine as _ce, text as _text

_DB_URL = os.environ.get("DATABASE_URL", "")
if _DB_URL:
    _engine = _ce(_DB_URL)
else:
    _engine = None
