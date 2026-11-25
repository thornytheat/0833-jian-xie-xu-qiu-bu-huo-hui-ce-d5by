from app.modules.pipeline import run


def find(data, code):
    return next(c for c in run(data, 4)["cases"] if c["case"]==code)


def test_case_0001(dirty):
    item = find(dirty, '0001')
    assert item['status'] == 'READY'


def test_case_0002(dirty):
    item = find(dirty, '0002')
    assert item['status'] == 'READY'


def test_case_0003(dirty):
    item = find(dirty, '0003')
    assert item['status'] == 'DUPLICATE_DAY'


def test_case_0004(dirty):
    item = find(dirty, '0004')
    assert item['status'] == 'SERVICE_TARGET_MISSED'


def test_clean_sample_applies_same_checks(clean):
    assert [case['status'] for case in run(clean,4)['cases']]==['READY','READY']


def test_decision_retains_calculated_difference(dirty):
    item=find(dirty,'0001')
    assert item['delta']==item['measure']['value']-item['measure']['expected']
