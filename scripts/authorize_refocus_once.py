"""Records the user's explicit one-call authorization for this refocus session."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import store
store.init()
with store.db() as c:
 c.execute('BEGIN IMMEDIATE')
 granted=c.execute("SELECT value FROM settings WHERE key='auth_refocus_20261121'").fetchone()
 if not granted:
  c.execute("INSERT INTO settings VALUES('auth_refocus_20261121','one-call authorized in chat')")
  c.execute("INSERT INTO settings VALUES('model_call_budget','1') ON CONFLICT(key) DO UPDATE SET value='1'")
 print('Existing authorization retained' if granted else 'One model call authorized; idempotent, no automatic replenishment')
