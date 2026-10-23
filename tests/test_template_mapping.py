import io
import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from webapp.app import app

client=TestClient(app)


def audit(data,template='sales',mapping=None):
    fields={'template':template}
    if mapping is not None:fields['mapping']=json.dumps(mapping)
    return client.post('/api/workspace',files={'file':('file.csv',data)},data=fields)


def test_familiar_headings_are_matched_without_renaming():
    data=b'Order Number,Purchase Date,Qty,Price Per Unit\n001,2025-01-01,2,10\n002,bad,0,-1\n'
    r=audit(data)
    assert r.status_code==200,r.text
    checks=r.json()['template_checks']
    assert [c['column'] for c in checks]==['Order Number','Purchase Date','Qty','Price Per Unit']
    assert [c['count'] for c in checks]==[0,1,1,1]
    assert '4 of 4 template checks applied' in r.json()['narrative']


def test_custom_columns_and_date_format_are_mapped_explicitly():
    data=b'Our Ref,When Bought,How Many,Each Cost\nA,31/12/2025,1,5\nB,invalid,2,6\n'
    mapping={'columns':{'order_id':'Our Ref','order_date':'When Bought','quantity':'How Many','unit_price':'Each Cost'},'date_format':'%d/%m/%Y'}
    result=audit(data,mapping=mapping)
    assert result.status_code==200,result.text
    checks=result.json()['template_checks']
    assert [c['count'] for c in checks]==[0,1,0,0]
    assert checks[1]['source_rows']==[3]


def test_ambiguous_matches_are_not_guessed_and_can_be_overridden():
    data=b'Order Number,Order ID,quantity\nA,A,1\n'
    result=audit(data).json()['template_checks']
    assert result[0]['status']=='not_checked'
    result=audit(data,mapping={'columns':{'order_id':'Order Number'}}).json()['template_checks']
    assert result[0]['column']=='Order Number' and result[0]['status']=='passed'


def test_explicit_unmapping_is_not_silently_replaced_with_a_guess():
    data=b'order_id,quantity\n1,1\n'
    result=audit(data,mapping={'columns':{'order_id':''}}).json()
    assert result['template_checks'][0]['status']=='not_checked'
    assert '1 of 4 template checks applied' in result['narrative']


@pytest.mark.parametrize('mapping',[
    {'columns':{'order_id':'not present'}},
    {'columns':{'order_id':'A','quantity':'A'}},
    {'columns':{'unknown':'A'}},
    {'columns':{'order_id':42}},
    {'date_format':'guess'},
    {'extra':True},
])
def test_invalid_mapping_fails_clearly(mapping):
    assert audit(b'A,B\n1,2\n',mapping=mapping).status_code==422


def test_numeric_excel_header_can_be_mapped_without_editing_source():
    source=io.BytesIO()
    pd.DataFrame({123:['A','B']}).to_excel(source,index=False)
    result=client.post('/api/workspace',files={'file':('headers.xlsx',source.getvalue())},data={'template':'inventory','mapping':json.dumps({'columns':{'sku':'123'}})})
    assert result.status_code==200,result.text
    assert result.json()['template_checks'][0]['column']=='123'
