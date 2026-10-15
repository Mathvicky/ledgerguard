"""Engine timing only; not a production-capacity benchmark."""
import json,platform,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from ledgerguard.engine import reconcile
header='id,vendor,reference,amount,currency,date\n'
payload={k:header+''.join(f'{k}-{i},Vendor {i},REF-{i},100.00,GBP,2026-09-01\n' for i in range(1000)) for k in ['invoices','payments','statements']}
values=[]
for _ in range(5):
    start=time.perf_counter();result=reconcile(payload);values.append(round((time.perf_counter()-start)*1000,3))
print(json.dumps(dict(python=platform.python_version(),platform=platform.system(),records=3000,runs_ms=values,cases=len(result['cases']),scope='Single-process engine only; 1000 separate vendor buckets. Not worst-case fuzzy matching or HTTP throughput.'),indent=2))
