from app.business import DomainIssue
from app.intake.service import inspect
from app.modules.calculate import build_plan, measure
from app.modules.expedite import decide
from app.modules.grouping import case_groups
from app.modules.policy import policy
from app.modules.prepare import prepare
from app.modules.reconcile import balance


def evaluate(rows, stage):
    case = {'case':rows[0]['case'],'records':[r['record'] for r in rows], 'status':'READY'}
    plan = None
    try:
        case['prep'], payload = prepare(rows)
        if stage >= 3:
            plan = build_plan(payload)
            case['measure'] = measure(plan)
        if stage >= 4:
            case.update(policy(case['measure']))
    except DomainIssue as error:
        case['status'] = error.code
    return case, plan


def signoff(intake, cases, checks, plan):
    """签发结论：来源结构守恒且加急后各备件均不超原缺货上限。"""
    structural = not intake['rejected'] and checks['balanced'] and bool(cases)
    reasons = []
    if not cases:
        reasons.append('NO_CASES')
    if intake['rejected']:
        reasons.append('ISOLATED_ROWS')
    if not checks['balanced']:
        reasons.append('ROWS_UNBALANCED')
    reasons.extend(plan['blocked'])
    return {'ready': not reasons, 'structural': structural,
            'expedite': not plan['hold'], 'reasons': reasons}


def run(data, stage=5, critical=()):
    intake = inspect(data)
    output = {'intake': {k:v for k,v in intake.items() if k!='rows'}}
    if stage == 1:
        return output
    evaluated = [evaluate(rows, stage) for _, rows in case_groups(intake['rows'])]
    cases = [case for case, _ in evaluated]
    plans = {case['case']: plan for case, plan in evaluated if plan is not None}
    unmeasured = [case['case'] for case, plan in evaluated if plan is None]
    output['cases'] = cases
    if stage >= 4:
        output['expedite'] = decide(plans, critical, unmeasured)
    if stage >= 5:
        output['balance'] = balance(intake,cases)
        output['signoff'] = signoff(intake, cases, output['balance'], output['expedite'])
    return output
