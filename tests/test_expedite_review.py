import io

import pytest

from app.business import DomainIssue
from app.modules.pipeline import run
from app.review.service import execute, review
from tests.test_expedite import source


def over_limit_batch(store):
    data = source([
        dict(case='0001', history=[(1,10)], demand=[(2,20)], stock=0, lead=2, limit=10000),
        dict(case='0002', history=[(1,1)], demand=[(1,4)], stock=0, lead=1, limit=0),
    ])
    return execute(store,data)


def test_expedite_over_limit_cannot_be_approved(store):
    batch = over_limit_batch(store)
    assert batch['report']['expedite']['hold'] is True
    assert batch['report']['signoff']['ready'] is False
    assert 'OVER_LIMIT:0002' in batch['report']['signoff']['reasons']
    with pytest.raises(DomainIssue,match='UNRESOLVED_ISSUES'):
        review(store,batch['id'],dict(revision=0,status='APPROVED',note='加急后再次核对'))
    assert store.load(batch['id'])['revision'] == 0


def test_expedite_over_limit_can_be_held(store):
    batch = over_limit_batch(store)
    output = review(store,batch['id'],dict(revision=0,status='HELD',note='加急后仍超上限'))
    assert (output['status'],output['revision']) == ('HELD',1)


def test_critical_mark_changes_run_identity(store, clean):
    plain = execute(store,clean)
    marked = execute(store,clean,['0002'])
    assert plain['id'] != marked['id']
    assert marked['report']['expedite']['critical'] == ['0002']
    assert marked['report']['manifest']['critical'] == ['0002']
    assert len(store.list()) == 2


def test_byte_identical_request_keeps_single_run(store, clean):
    first = execute(store,clean,['0002'])
    second = execute(store,clean,'0002')
    assert first == second and len(store.list()) == 1


def test_critical_mark_is_recorded_in_evidence(store, clean):
    import json
    from app.evidence.render import artifact
    run_row = execute(store,clean,['0002'])
    packet = json.loads(artifact(run_row))
    assert packet['expedite']['critical'] == ['0002']
    assert packet['manifest']['critical'] == ['0002']
    assert packet['expedite']['selected'] is not None


def test_run_rejects_approval_when_unmeasured_case(store):
    data = source([
        dict(case='0001', history=[(1,10)], demand=[(2,20)], stock=0, lead=2, limit=10000),
        dict(case='0002', history=[(1,1)], demand=[(1,4)], stock=0, lead=1, limit=10000),
    ]).replace(b'0002d1,0002,demand,1,4',
               b'0002d1,0002,demand,1,4\r\n0002x1,0002,history,1,7')
    batch = execute(store,data)
    assert batch['report']['expedite']['hold'] is True
    assert '0002' in batch['report']['expedite']['unmeasured']


def test_stage_preview_accepts_critical_without_writing(client):
    response = client.post('/api/stages/balance',data={'sample':'clean','critical':'0002'})
    assert response.status_code == 200
    assert response.json['expedite']['critical'] == ['0002']
    assert client.get('/api/runs').json == {'items':[]}


def test_run_accepts_repeated_critical_fields(client):
    response = client.post('/api/runs',data={'sample':'clean','critical':['0002','0002']})
    assert response.status_code == 200
    assert response.json['report']['expedite']['critical'] == ['0002']


def test_upload_and_sample_share_identity_with_marks(client, clean):
    by_sample = client.post('/api/runs',data={'sample':'clean','critical':'0002'}).json
    by_file = client.post('/api/runs',data={
        'file':(io.BytesIO(clean),'input.csv'),'critical':'0002'}).json
    assert by_sample['id'] == by_file['id']


def test_marked_run_download_keeps_selection(client):
    batch = client.post('/api/runs',data={'sample':'clean','critical':'0002'}).json
    evidence = client.get('/api/runs/'+batch['id']+'/evidence').json
    assert evidence['expedite']['critical'] == ['0002']
    assert evidence['expedite']['selected']['case'] == '0001'
