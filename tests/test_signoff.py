import pytest

from app.modules.pipeline import run
from tests.test_expedite import source


def test_expedite_rescues_case_over_limit():
    data = source([dict(case='0001', history=[(1,2)], demand=[(2,5)], stock=0, lead=2, limit=8000)])
    report = run(data,5)
    assert report['cases'][0]['status'] == 'SERVICE_TARGET_MISSED'
    assert report['expedite']['cases']['0001']['baseline']['rate'] == 10000
    assert report['expedite']['cases']['0001']['outcome']['rate'] == 6000
    assert report['expedite']['hold'] is False
    assert report['signoff']['ready'] is True


def test_limit_is_inclusive_after_expedite():
    at_limit = run(source([dict(case='0001', history=[(1,2)], demand=[(2,5)], stock=0,
                                lead=2, limit=6000)]),5)
    below = run(source([dict(case='0001', history=[(1,2)], demand=[(2,5)], stock=0,
                            lead=2, limit=5999)]),5)
    assert at_limit['signoff']['ready'] is True
    assert below['signoff']['ready'] is False
    assert below['expedite']['over_limit'] == ['0001']


def test_isolated_rows_block_signoff_even_if_expedite_within_limit(dirty):
    report = run(dirty,5)
    assert report['expedite']['hold'] is True
    assert 'UNMEASURED:0003' in report['signoff']['reasons']
    assert report['signoff']['structural'] is False
    assert 'ISOLATED_ROWS' in report['signoff']['reasons']


def test_clean_sample_signs_off_with_selection(clean):
    report = run(clean,5)
    assert report['signoff']['ready'] is True
    assert report['expedite']['hold'] is False
    assert report['expedite']['selected']['case'] == '0001'
