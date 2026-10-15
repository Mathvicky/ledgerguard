"""Explainable synthetic AP reconciliation. Integer minor units; no currency mixing."""
import csv
import io
import re
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation

FIELDS = {"invoices": ["id","vendor","reference","amount","currency","date"], "payments": ["id","vendor","reference","amount","currency","date"], "statements": ["id","vendor","reference","amount","currency","date"]}

def normalize(value):
    return re.sub(r"[^a-z0-9]", "", value.casefold())

def money(value):
    try:
        if not re.fullmatch(r"\d+(?:\.\d{1,2})?",str(value)): raise ValueError("invalid decimal amount")
        value = Decimal(str(value))
        if not value.is_finite() or value <= 0 or value > 1000000000 or value.as_tuple().exponent < -2:
            raise ValueError("amount must be positive, <= 1 billion, and have at most two decimals")
        return int(value * 100)
    except InvalidOperation:
        raise ValueError("invalid decimal amount") from None

def parse_csv(text, kind):
    if kind not in FIELDS: raise ValueError("unknown dataset")
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    if reader.fieldnames != FIELDS[kind]: raise ValueError(f"{kind}: headers must be {','.join(FIELDS[kind])}")
    rows=[]; ids=set()
    for number, row in enumerate(reader,2):
        if len(rows)>=2000: raise ValueError("maximum 2000 rows per dataset")
        if None in row or any(v is None or not v.strip() or len(v)>200 for v in row.values()): raise ValueError(f"{kind} row {number}: missing, extra or oversized field")
        row={k:v.strip() for k,v in row.items()}
        if row['id'] in ids: raise ValueError(f"{kind} row {number}: duplicate id")
        ids.add(row['id'])
        if not re.fullmatch(r"[A-Z]{3}",row['currency']): raise ValueError("currency must be three uppercase letters")
        date.fromisoformat(row['date'])
        if not normalize(row['vendor']) or not normalize(row['reference']): raise ValueError("vendor and reference need letters or digits")
        row['minor']=money(row['amount']); rows.append(row)
    return rows

def near(a,b):
    # Deliberately bounded: one insertion/deletion/substitution, not unrestricted fuzzy matching.
    if a==b:return True
    if abs(len(a)-len(b))>1 or min(len(a),len(b))<4:return False
    if len(a)==len(b):return sum(x!=y for x,y in zip(a,b))==1
    if len(a)>len(b):a,b=b,a
    i=j=errors=0
    while i<len(a) and j<len(b):
        if a[i]==b[j]:i+=1;j+=1
        else:
            errors+=1;j+=1
            if errors>1:return False
    return True

def reconcile(payload):
    if not isinstance(payload,dict):raise ValueError("expected dataset object")
    datasets={k:parse_csv(payload.get(k,''),k) for k in FIELDS}
    invoices,payments,statements=(datasets[k] for k in FIELDS)
    cases=[]
    def key(row):return normalize(row['vendor']),normalize(row['reference']),row['currency']
    def emit(kind, records, amount, currency, explanation):
        cases.append(dict(id=f"CASE-{len(cases)+1:04}",kind=kind,records=records,amount_minor=amount,currency=currency,explanation=explanation,status="open",audit=[]))
    index=defaultdict(list)
    for row in invoices:index[key(row)].append(row)
    # Each cluster produces one finding so pairs do not multiply financial exposure.
    groups=defaultdict(list)
    for row in invoices:groups[(normalize(row['vendor']),row['currency'],row['minor'])].append(row)
    for group in groups.values():
        used=set()
        for i,a in enumerate(group):
            if i in used:continue
            cluster=[a]
            for j in range(i+1,len(group)):
                b=group[j]
                if j not in used and abs((date.fromisoformat(a['date'])-date.fromisoformat(b['date'])).days)<=7 and near(normalize(a['reference']),normalize(b['reference'])):
                    cluster.append(b);used.add(j)
            if len(cluster)>1:
                emit('possible_duplicate',[r['id'] for r in cluster],a['minor']*(len(cluster)-1),a['currency'],'Same normalized supplier, currency and amount; reference differs by at most one character within seven days. Verify before recovery.')
    paid=defaultdict(list)
    for row in payments:paid[key(row)].append(row)
    for k,group in paid.items():
        expected=index.get(k,[]); total=sum(r['minor'] for r in group)
        if not expected:emit('unmatched_payment',[r['id'] for r in group],total,k[2],'Payment has no invoice with the same normalized supplier, reference and currency.')
        else:
            expected_total=sum(r['minor'] for r in expected)
            if total>expected_total:emit('overpayment',[r['id'] for r in expected+group],total-expected_total,k[2],'Total payments exceed total recorded invoice value for this exact normalized reference.')
    statement_groups=defaultdict(list)
    for row in statements:statement_groups[key(row)].append(row)
    for k,group in statement_groups.items():
        expected=index.get(k,[]); amount=sum(r['minor'] for r in group)
        if not expected:emit('missing_invoice',[r['id'] for r in group],amount,k[2],'Supplier statement reference is missing from the invoice ledger. Statement amounts represent original invoice values, not outstanding balances.')
        else:
            ledger=sum(r['minor'] for r in expected)
            if amount!=ledger:emit('statement_difference',[r['id'] for r in expected+group],abs(amount-ledger),k[2],'Statement original invoice total differs from the ledger total; this is not a recovered amount.')
    cases.sort(key=lambda c:(c['currency'],-c['amount_minor'],c['id']))
    return dict(cases=cases,counts={k:len(v) for k,v in datasets.items()},rules_version="1.0",note="Case amounts may overlap. Do not sum them as recoverable savings.")
