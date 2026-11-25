from datetime import datetime, timezone
from hashlib import sha256
from time import monotonic

from app.business import DomainIssue
from app.config import RULE_VERSION
from app.modules.expedite import normalize
from app.modules.pipeline import run


def now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


def execute(store, data, critical=()):
    start = monotonic()
    critical = normalize(critical)
    fingerprint = sha256(data).hexdigest()
    identity = f'{RULE_VERSION}:{fingerprint}'
    if critical:
        identity += ':' + ','.join(critical)
    run_id = sha256(identity.encode()).hexdigest()
    try:
        return store.load(run_id)
    except DomainIssue as error:
        if error.code != 'RUN_NOT_FOUND':
            raise
    report = run(data, critical=critical)
    report['manifest'] = dict(sha256=fingerprint, version=RULE_VERSION, created=now(),
                              duration_ms=round((monotonic()-start)*1000,3), bytes=len(data),
                              critical=list(critical), run_id=run_id)
    return store.register(run_id,report)


def review(store, run_id, values):
    if not isinstance(values, dict):
        raise DomainIssue('REVIEW_FIELDS')
    revision, status, note = (values.get(key) for key in ('revision','status','note'))
    if type(revision) is not int or revision < 0 or status not in ('APPROVED','HELD') or not isinstance(note,str) or not (3<=len(note.strip())<=200):
        raise DomainIssue('REVIEW_FIELDS')
    current = store.load(run_id)
    if revision != current['revision']:
        raise DomainIssue('STALE_REVIEW')
    if current['status'] == 'APPROVED':
        raise DomainIssue('RUN_FINALIZED')
    if status == 'APPROVED' and not signoff_ready(current['report']):
        raise DomainIssue('UNRESOLVED_ISSUES')
    return store.revise(run_id,revision,status,note.strip(),now())


def signoff_ready(report):
    """旧批次没有加急结论时退回到原缺货对账判定。"""
    if 'signoff' in report:
        return report['signoff']['ready']
    return report['balance']['releasable']
