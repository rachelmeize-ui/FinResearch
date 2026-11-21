import sqlite3,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
target=Path(sys.argv[1]).resolve()
if not target.is_relative_to(root/'test-results'):raise ValueError('Test copy must remain inside test-results')
target.parent.mkdir(parents=True,exist_ok=True)
with sqlite3.connect(root/'data/workspace.sqlite3') as source,sqlite3.connect(target) as dest:source.backup(dest)
