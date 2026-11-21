import io
import json
import sys
import time
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
import test_core
phase=sys.argv[1] if len(sys.argv)>1 else 'final'
suite=unittest.defaultTestLoader.loadTestsFromTestCase(test_core.RegressionTests) if phase=='initial' else unittest.defaultTestLoader.discover(str(ROOT/'tests'))
buf=io.StringIO();started=time.perf_counter();result=unittest.TextTestRunner(stream=buf,verbosity=2).run(suite)
out=ROOT/'test-results';out.mkdir(exist_ok=True)
(out/(phase+'.txt')).write_text(buf.getvalue(),encoding='utf-8')
report=dict(phase=phase,tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),seconds=round(time.perf_counter()-started,3),failure_details=[{'test':str(t),'trace':trace} for t,trace in result.failures+result.errors])
(out/(phase+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True));sys.exit(0 if result.wasSuccessful() else 1)
