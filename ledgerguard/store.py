import json
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from .engine import reconcile

@contextmanager
def db():
    conn=sqlite3.connect(os.getenv("LEDGERGUARD_DB","ledgerguard.db"),timeout=15)
    conn.row_factory=sqlite3.Row
    try:
        with conn:yield conn
    finally:conn.close()

def initialize():
    with db() as c:
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, payload TEXT, state TEXT, attempts INTEGER, available REAL, lease REAL, result TEXT, error TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS cases(job_id TEXT,id TEXT,body TEXT,PRIMARY KEY(job_id,id))")

def submit(payload):
    # Validate synchronously; invalid data must never enter the retry queue.
    from .engine import FIELDS,parse_csv
    if not isinstance(payload,dict):raise ValueError("Expected a dataset object")
    for k in FIELDS:parse_csv(payload.get(k,''),k)
    job=uuid.uuid4().hex
    with db() as c:c.execute("INSERT INTO jobs VALUES(?,?,'queued',0,?,0,NULL,NULL)",(job,json.dumps(payload),time.time()))
    return job

def status(job):
    with db() as c:
        row=c.execute("SELECT id,state,attempts,result,error FROM jobs WHERE id=?",(job,)).fetchone()
        if row is None:return None
        result=dict(row);result['result']=json.loads(result['result']) if result['result'] else None
        if result['result'] is not None:
            result['result']['cases']=[json.loads(r[0]) for r in c.execute("SELECT body FROM cases WHERE job_id=? ORDER BY id",(job,))]
        if result['result'] is not None:
            result['result']['cases'].sort(key=lambda c:(c['currency'],-c['amount_minor'],c['id']))
        return result

def tick(processor=reconcile):
    now=time.time()
    with db() as c:
        c.execute("BEGIN IMMEDIATE")
        # A crashed worker's expired lease is retried, or dead-lettered at the attempt bound.
        c.execute("UPDATE jobs SET state=CASE WHEN attempts>=3 THEN 'dead' ELSE 'queued' END,error='Worker lease expired' WHERE state='running' AND lease<?",(now,))
        row=c.execute("SELECT * FROM jobs WHERE state='queued' AND available<=? ORDER BY available LIMIT 1",(now,)).fetchone()
        if row is None:return False
        c.execute("UPDATE jobs SET state='running', attempts=attempts+1,lease=? WHERE id=?",(now+120,row['id']))
    try:
        result=processor(json.loads(row['payload']))
        with db() as c:
            # Attempt is a fencing token: an expired worker cannot overwrite its successor.
            current=c.execute("SELECT state,attempts FROM jobs WHERE id=?",(row['id'],)).fetchone()
            if current['state']!='running' or current['attempts']!=row['attempts']+1:return True
            for case in result['cases']:c.execute("INSERT OR REPLACE INTO cases VALUES(?,?,?)",(row['id'],case['id'],json.dumps(case)))
            c.execute("UPDATE jobs SET state='complete',result=?,error=NULL WHERE id=?",(json.dumps(result),row['id']))
    except Exception:
        attempt=row['attempts']+1
        with db() as c:c.execute("UPDATE jobs SET state=?,available=?,error='Processing failed; inspect worker logs' WHERE id=? AND state='running' AND attempts=?",('dead' if attempt>=3 else 'queued',time.time()+2**attempt,row['id'],attempt))
    return True

def transition(job,case_id,new_status,note):
    if not isinstance(note,str) or not note.strip() or len(note)>500:raise ValueError('Provide a note of 1..500 characters')
    allowed={'open':{'investigating','dismissed'},'investigating':{'resolved','dismissed'},'resolved':set(),'dismissed':set()}
    with db() as c:
        c.execute("BEGIN IMMEDIATE")
        row=c.execute("SELECT body FROM cases WHERE job_id=? AND id=?",(job,case_id)).fetchone()
        if row is None:raise ValueError('Unknown case')
        body=json.loads(row[0]);old=body['status']
        if new_status not in allowed[old]:raise ValueError('Invalid case transition')
        body['status']=new_status;body['audit'].append(dict(at=time.time(),previous=old,status=new_status,note=note.strip(),actor='local-demo-user'))
        c.execute("UPDATE cases SET body=? WHERE job_id=? AND id=?",(json.dumps(body),job,case_id))
    return body
