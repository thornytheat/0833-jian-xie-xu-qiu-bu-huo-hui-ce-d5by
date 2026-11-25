from app.business import measured


def compute(data):
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
    stock, unserved, requested, in_transit = scenario['quantity'],0,0,0
    schedule = {}
    for day in range(1,7):
        arrival = schedule.get(day,0)
        in_transit -= arrival
        stock += arrival+series['receipt'].get(day,0)
        demand = series['demand'].get(day,0)
        requested += demand
        unserved += max(0,demand-stock)
        stock = max(0,stock-demand)
        if stock+in_transit < target:
            order = target-stock-in_transit
            schedule[day+scenario['lead_time']] = order
            in_transit += order
    rate = (10000*unserved+requested-1)//requested if requested else 0
    return measured(rate,scenario['basis_points'],'基点',{'forecast':str(forecast),'reorder':target,'unserved':unserved,'requested':requested,'orders':{str(k):v for k,v in schedule.items()},'closing':stock})
