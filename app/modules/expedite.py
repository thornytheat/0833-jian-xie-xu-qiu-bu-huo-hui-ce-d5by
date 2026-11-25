"""首日收盘后的加急决策：全仓最多提前一笔在途到货，先到货再扣当天需求。

选择规则：优先减少关键件缺货量，关键件缺货量相同时再比较全仓缺货量。
任一业务组加急后仍超过原缺货上限（服务目标基点）时整仓暂缓签发。
"""

from app.modules.calculate import simulate

DAY = 1                   # 首日收盘时点
EXPEDITE_DAY = 2          # 提前到次日
EARLIEST_SOURCE_DAY = 3   # 原定第三天或更晚的到货才可加急


def normalize(value):
    """把表单或调用方给出的标记整理为去重排序的业务组编号。"""
    if value is None:
        return ()
    pieces = value.replace('，', ',').split(',') if isinstance(value, str) else value
    return tuple(sorted({str(piece).strip() for piece in pieces if str(piece).strip()}))


def candidates(plan):
    """某业务组原定第三天或更晚、数量为正的到货。"""
    return [(day, quantity) for day, quantity in sorted(plan['orders'].items())
            if day >= EARLIEST_SOURCE_DAY and quantity > 0]


def move(orders, day):
    """把某天到货整笔挪到次日，原到货日删除，保证对账只入库一次。"""
    schedule = dict(orders)
    quantity = schedule.pop(day)
    schedule[EXPEDITE_DAY] = schedule.get(EXPEDITE_DAY, 0) + quantity
    return schedule, quantity


def replay(plan, schedule):
    return simulate(plan['series'], plan['scenario'], schedule)


def _score(outcomes, critical):
    shortage = sum(outcome['unserved'] for case, outcome in outcomes.items() if case in critical)
    total = sum(outcome['unserved'] for outcome in outcomes.values())
    return shortage, total


def _snapshot(outcome):
    return {'unserved': outcome['unserved'], 'requested': outcome['requested'],
            'rate': outcome['rate'], 'closing': outcome['closing']}


def _wire(orders):
    return {str(day): quantity for day, quantity in sorted(orders.items())}


def decide(plans, critical=(), unmeasured=()):
    """在全部业务组的候选到货中挑一笔，返回加急选择和签发结论。

    ``plans`` 以业务组编号为键，值为 ``calculate.build_plan`` 的结果。
    ``unmeasured`` 是无法模拟的业务组；无法确认其上限时整仓暂缓。
    """
    critical = set(normalize(critical))
    unmeasured = sorted(set(normalize(unmeasured)))
    before = {case: plan['baseline'] for case, plan in plans.items()}
    baseline_score = _score(before, critical)

    best = None
    for case in sorted(plans):
        plan = plans[case]
        for day, quantity in candidates(plan):
            schedule, moved = move(plan['orders'], day)
            after = dict(before)
            after[case] = replay(plan, schedule)
            score = _score(after, critical)
            key = score + (day, case, moved)
            if best is None or key < best[0]:
                best = (key, case, schedule, day, moved, after)

    selected = None
    chosen = before
    if best and best[0][:2] < baseline_score:
        _, case, schedule, day, moved, after = best
        original = sum(plans[case]['orders'].values())
        stocked_once = sum(schedule.values()) == original
        selected = {
            'case': case,
            'from_day': day,
            'to_day': EXPEDITE_DAY,
            'quantity': moved,
            'orders': _wire(schedule),
            'removed_day': day,
            'stocked_once': stocked_once,
        }
        chosen = after

    outcome_score = _score(chosen, critical)
    over_limit = [case for case in sorted(plans)
                  if chosen[case]['rate'] > plans[case]['scenario']['basis_points']]
    blocked = [f'OVER_LIMIT:{case}' for case in over_limit]
    blocked += [f'UNMEASURED:{case}' for case in unmeasured]
    hold = bool(blocked)

    cases = {}
    for case in sorted(plans):
        plan = plans[case]
        limit = plan['scenario']['basis_points']
        item = {
            'critical': case in critical,
            'limit': limit,
            'orders': _wire(plan['orders']),
            'baseline': _snapshot(plan['baseline']),
            'outcome': _snapshot(chosen[case]),
            'within_limit': chosen[case]['rate'] <= limit,
        }
        if selected and selected['case'] == case:
            item.update(from_day=selected['from_day'], to_day=selected['to_day'],
                        quantity=selected['quantity'], removed_day=selected['removed_day'],
                        expedited_orders=selected['orders'],
                        stocked_once=selected['stocked_once'])
        cases[case] = item
    for case in unmeasured:
        cases[case] = {'critical': case in critical, 'limit': None, 'orders': {},
                       'baseline': None, 'outcome': None, 'within_limit': False}

    return {
        'day': DAY,
        'expedite_day': EXPEDITE_DAY,
        'earliest_source_day': EARLIEST_SOURCE_DAY,
        'critical': sorted(critical),
        'missing_critical': sorted(critical - set(plans)),
        'unmeasured': unmeasured,
        'selected': selected,
        'baseline': {'critical_unserved': baseline_score[0], 'total_unserved': baseline_score[1]},
        'outcome': {'critical_unserved': outcome_score[0], 'total_unserved': outcome_score[1]},
        'hold': hold,
        'blocked': blocked,
        'over_limit': over_limit,
        'cases': dict(sorted(cases.items())),
    }
