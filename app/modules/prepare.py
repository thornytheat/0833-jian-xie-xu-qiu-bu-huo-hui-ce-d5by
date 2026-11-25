from app.business import DomainIssue, prepared, single


def prepare(rows):
    scenario = single(rows,'scenario')
    cutoff,lead,alpha = scenario['day'],scenario['lead_time'],scenario['alpha']
    if not 0 < cutoff <= 3650 or not 0 < lead <= 60 or not 0 < alpha <= 10000 or scenario['basis_points']>10000:
        raise DomainIssue('INVALID_SCENARIO')
    series = {'history':{},'demand':{},'receipt':{}}
    for row in rows:
        kind = row['kind']
        if kind=='scenario':
            continue
        day = row['day']
        if day in series[kind]:
            raise DomainIssue('DUPLICATE_DAY')
        if not 1 <= day <= (cutoff if kind=='history' else 6):
            raise DomainIssue('DAY_OUT_OF_RANGE')
        series[kind][day] = row['quantity']
    points = sorted((day,n) for day,n in series['history'].items() if n)
    if len(points)>400:
        raise DomainIssue('HISTORY_LIMIT')
    return prepared(len(points),{'history_days':cutoff,'lead_days':lead},(series,points,scenario))
