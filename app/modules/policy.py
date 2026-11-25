from app.business import decision


def policy(result):
    return decision(result,'SERVICE_TARGET_MISSED' if result['value']>result['expected'] else None,upper_bound=True)
