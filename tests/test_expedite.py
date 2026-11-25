import io
import csv

import pytest

from app.modules.expedite import decide, normalize
from app.modules.pipeline import run

HEADER = ('record','case','kind','day','quantity','lead_time','alpha','basis_points','note')


def source(cases):
    stream = io.StringIO(newline='')
    sink = csv.writer(stream)
    sink.writerow(HEADER)
    for case in cases:
        code = case['case']
        for day, quantity in case.get('history', []):
            sink.writerow([f'{code}h{day}',code,'history',day,quantity,0,0,0,''])
        for day, quantity in case.get('demand', []):
            sink.writerow([f'{code}d{day}',code,'demand',day,quantity,0,0,0,''])
        for day, quantity in case.get('receipt', []):
            sink.writerow([f'{code}r{day}',code,'receipt',day,quantity,0,0,0,''])
        sink.writerow([f'{code}s',code,'scenario',case.get('cutoff',6),case.get('stock',0),
                       case.get('lead',2),case.get('alpha',10000),case.get('limit',10000),''])
    return stream.getvalue().encode()


def plan_of(cases, critical=()):
    return run(source(cases),5,critical)['expedite']


def test_normalize_accepts_lists_and_delimited_forms():
    assert normalize('0002, 0001，0002') == ('0001','0002')
    assert normalize(['0003','0001','0003']) == ('0001','0003')
    assert normalize(None) == ()


def test_unmarked_batch_compares_whole_warehouse():
    cases = [
        dict(case='0001', history=[(1,10)], demand=[(2,20)], stock=0, lead=2),
        dict(case='0002', history=[(1,1)], demand=[(2,5)], stock=0, lead=2),
    ]
    result = plan_of(cases)
    # 0001 的候选到货能减少 10 件缺货，0002 只能减少 1 件
    assert result['selected']['case'] == '0001'
    assert result['selected']['from_day'] == 3
    assert result['selected']['quantity'] == 10
    assert result['baseline']['total_unserved'] == 25
    assert result['outcome']['total_unserved'] == 15


def test_critical_shortage_outranks_whole_warehouse():
    cases = [
        dict(case='0001', history=[(1,10)], demand=[(2,20)], stock=0, lead=2),
        dict(case='0002', history=[(1,1)], demand=[(2,5)], stock=0, lead=2),
    ]
    result = plan_of(cases, ['0002'])
    # 关键件 0002 的缺货优先，即使全仓减少量更小
    assert result['critical'] == ['0002']
    assert result['selected']['case'] == '0002'
    assert result['baseline']['critical_unserved'] == 5
    assert result['outcome']['critical_unserved'] == 4
    assert result['baseline']['total_unserved'] == 25
    assert result['outcome']['total_unserved'] == 24


def test_tie_on_critical_falls_back_to_whole_warehouse():
    cases = [
        dict(case='0001', history=[(1,10)], demand=[(2,20)], stock=0, lead=2),
        dict(case='0002', history=[(1,1)], demand=[(2,5)], stock=0, lead=2),
    ]
    result = plan_of(cases, ['0001','0002'])
    # 两者都无法消除关键件缺货时，按全仓缺货量比较
    assert result['selected']['case'] == '0001'
    assert result['outcome']['critical_unserved'] < result['baseline']['critical_unserved']


def test_only_day_three_or_later_is_eligible():
    cases = [dict(case='0001', history=[(1,10)], demand=[(1,20)], stock=0, lead=1)]
    result = plan_of(cases)
    # 唯一到货在第 2 天，不属于第三天或更晚的在途货
    assert result['selected'] is None
    assert result['cases']['0001']['orders'] == {'2': 5}


def test_expedite_lands_next_day_and_stays_in_stock_once():
    cases = [dict(case='0001', history=[(1,10)], demand=[(2,20)], stock=0, lead=2)]
    result = plan_of(cases)
    selected = result['selected']
    assert (selected['from_day'], selected['to_day']) == (3,2)
    assert selected['orders'] == {'2': 10}
    assert '3' not in selected['orders']
    assert selected['stocked_once'] is True
    # 加急前后在途总量一致：只挪日，不新增一次入库
    assert sum(selected['orders'].values()) == sum(result['cases']['0001']['orders'].values())


def test_hold_when_any_case_still_over_original_limit():
    cases = [
        dict(case='0001', history=[(1,10)], demand=[(2,20)], stock=0, lead=2, limit=0),
        dict(case='0002', history=[(1,1)], demand=[(1,4)], stock=0, lead=1, limit=0),
    ]
    result = plan_of(cases)
    assert result['hold'] is True
    assert '0002' in result['over_limit']
    assert 'OVER_LIMIT:0002' in result['blocked']


def test_releasable_when_all_within_limit():
    cases = [dict(case='0001', history=[(1,10)], demand=[(2,20)], stock=0, lead=2, limit=10000)]
    result = plan_of(cases)
    assert result['hold'] is False


def test_unmeasured_case_blocks_release():
    cases = [
        dict(case='0001', history=[(1,10)], demand=[(2,20)], stock=0, lead=2, limit=10000),
        dict(case='0002', history=[(1,1)], demand=[(1,4)], stock=0, lead=1, limit=10000),
    ]
    data = source(cases)
    # 让 0002 冲突，无法模拟
    data = data.replace(b'0002d1,0002,demand,1,4',
                        b'0002d1,0002,demand,1,4\r\n0002x1,0002,history,1,7')
    result = run(data,5)['expedite']
    assert '0002' in result['unmeasured']
    assert result['hold'] is True


def test_missing_critical_is_reported_without_crashing():
    result = decide({}, ['0009'])
    assert result['missing_critical'] == ['0009']
    assert result['selected'] is None
    assert result['hold'] is False


def test_clean_sample_selects_day_four_replenishment():
    from pathlib import Path
    data = (Path(__file__).resolve().parents[1] / 'sample_data' / 'ready.csv').read_bytes()
    result = run(data,5)['expedite']
    assert result['selected']['case'] == '0001'
    assert result['selected']['from_day'] == 4
    assert result['selected']['quantity'] == 2
    assert run(data,5)['signoff']['ready'] is True
