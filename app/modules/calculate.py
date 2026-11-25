from app.business import measured


def basis_points(unserved, requested):
    """未满足量占比，向上取整为基点。"""
    return (10000*unserved+requested-1)//requested if requested else 0


def simulate(series, scenario, schedule):
    """按固定到货计划回放六天：先到货，再扣当天需求，缺货计为失销。"""
    stock, unserved, requested = scenario['quantity'], 0, 0
    for day in range(1,7):
        stock += schedule.get(day,0)+series['receipt'].get(day,0)
        demand = series['demand'].get(day,0)
        requested += demand
        unserved += max(0,demand-stock)
        stock = max(0,stock-demand)
    return dict(unserved=unserved, requested=requested, closing=stock,
                rate=basis_points(unserved,requested))


def build_plan(data):
    """用精确分数求预测与补货点，并生成原始六天到货计划。"""
    from fractions import Fraction
    from math import ceil
    series,points,scenario = data
    alpha = Fraction(scenario['alpha'],10000)
    forecast = Fraction(0)
    if points:
        previous,quantity = points[0]
        interval = Fraction(previous)
        quantity = Fraction(quantity)
        for day,value in points[1:]:
            interval = interval*(1-alpha)+(day-previous)*alpha
            quantity = quantity*(1-alpha)+value*alpha
            previous = day
        forecast = quantity/interval*(1-alpha/2)
    target = ceil(forecast*scenario['lead_time'])
    stock, in_transit = scenario['quantity'],0
    schedule = {}
    for day in range(1,7):
        arrival = schedule.get(day,0)
        in_transit -= arrival
        stock += arrival+series['receipt'].get(day,0)
        demand = series['demand'].get(day,0)
        stock = max(0,stock-demand)
        if stock+in_transit < target:
            order = target-stock-in_transit
            schedule[day+scenario['lead_time']] = order
            in_transit += order
    return dict(series=series, scenario=scenario, forecast=forecast, reorder=target,
                orders=schedule, baseline=simulate(series,scenario,schedule))


def evidence(plan):
    outcome = plan['baseline']
    return {'forecast':str(plan['forecast']),'reorder':plan['reorder'],
            'unserved':outcome['unserved'],'requested':outcome['requested'],
            'orders':{str(k):v for k,v in plan['orders'].items()},'closing':outcome['closing']}


def measure(plan):
    return measured(plan['baseline']['rate'],plan['scenario']['basis_points'],'基点',evidence(plan))


def compute(data):
    return measure(build_plan(data))
