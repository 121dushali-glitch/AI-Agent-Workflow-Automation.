import pandas as pd
from src.tools import business_tools as bt


def test_wf001_explicit_threshold_overrides_column():
    data = {'CSV': pd.DataFrame({'Product': ['A', 'B'], 'Current Stock': [8, 30], 'Minimum Stock': [5, 5]})}
    assert bt.inventory_restock(data).empty
    assert bt.inventory_restock(data, threshold=10)['Product'].tolist() == ['A']


def test_wf002_uses_sku_to_match_vendor_list():
    data = {'Products': pd.DataFrame({'SKU': ['A1'], 'Product': ['Mouse'], 'Internal Price': [100]}),
            'Vendor_Prices': pd.DataFrame({'SKU': ['A1'], 'Vendor Price': [130]})}
    r = bt.price_validation(data)
    assert r.iloc[0]['Match Basis'] == 'SKU' and bool(r.iloc[0]['Exception'])


def test_wf003_flags_missing_sku_and_name_and_normalizes_columns():
    data = {'Vendors': pd.DataFrame({'SKU': ['A', None, 'C'], 'Product Name': ['x', 'y', None], 'Vendor Price': [1, 2, 3]})}
    r = bt.vendor_validation(data)
    assert r['validation_summary']['invalid_rows'] == 2 and len(r['cleaned_data']) == 1
    assert 'vendor_price' in r['cleaned_data'].columns


def test_wf003_warns_when_no_sku_column():
    data = {'Vendors': pd.DataFrame({'Product': ['x'], 'Vendor Price': [1]})}
    assert bt.vendor_validation(data)['validation_summary']['warnings']


def test_wf004_never_invents_missing_attributes():
    out = bt.description_generator({'Products': pd.DataFrame({'Product': ['Mug']})}).iloc[0]
    text = (out['Product Description'] + out['Short Description'] + out['Meta Description']).lower()
    assert 'practical features' not in text and 'everyday use' not in text
    assert 'category' in out['Missing Information'] and 'Incomplete' in out['Status']


def test_wf004_uses_only_provided_facts():
    df = pd.DataFrame({'Product': ['Mug'], 'Category': ['Kitchen'], 'Material': ['ceramic'], 'Color': ['blue']})
    out = bt.description_generator({'Products': df}).iloc[0]
    assert 'ceramic' in out['Product Description'] and 'blue' in out['Product Description']
    assert out['Missing Information'] == 'attributes, audience'


def test_wf006_blank_skus_are_not_definite_and_groups_exist():
    df = pd.DataFrame({'SKU': [None, None, 'S1', 'S1'], 'Product': ['Alpha', 'Zeta', 'Lamp', 'Desk Lamp']})
    r = bt.duplicate_products({'Products': df})
    assert r[r['SKU Match']].shape[0] == 1 and r['Group ID'].iloc[0].startswith('G')
    assert not ((r['Product A'] == 'Alpha') & (r['Confidence'] == 'Definite')).any()


def test_wf007_includes_products_and_timeline():
    data = {'Campaign': pd.DataFrame({'Campaign Goal': ['Launch'], 'Start Date': ['2026-01-01'], 'End Date': ['2026-01-07'], 'Product List': ['Mug, Cup']})}
    r = bt.campaign_brief(data, '')
    assert r['products'] == ['Mug', 'Cup'] and any('7 days' in t for t in r['timeline'])


def test_wf008_uses_only_four_intents_removes_duplicates_and_maps_categories():
    data = {'Keywords': pd.DataFrame({'Keyword': ['buy mouse', 'Buy Mouse', 'how to pick a mouse', 'best mouse', 'mouse login page', 'mouse']}),
            'Products': pd.DataFrame({'Product': ['Wireless Mouse']})}
    r = bt.keyword_classification(data)
    assert set(r['Intent']) <= {'informational', 'commercial', 'transactional', 'navigational'}
    assert len(r) == 5 and r.attrs['duplicates_removed'] == 1
    assert (r['Category'] == 'Wireless Mouse').all() and r.iloc[0]['Priority'] == 'High'


def _emps(skill, workload):
    return {'Employees': pd.DataFrame({'Employee': ['A'], 'Skills': [skill], 'Workload': [workload]})}


def test_wf009_escalates_when_nobody_has_the_skill():
    assert bt.task_assignment(_emps('java', 2), 'assign python task')['status'] == 'escalate'


def test_wf009_escalates_when_nobody_has_capacity():
    assert bt.task_assignment(_emps('python', 50), 'assign python task')['status'] == 'escalate'


def test_wf009_picks_skilled_available_employee_with_reasoning():
    data = {'Employees': pd.DataFrame({'Employee': ['A', 'B'], 'Skills': ['Python', 'Java'], 'Workload': [5, 1]})}
    r = bt.task_assignment(data, 'Assign urgent python task by Friday')
    assert r.iloc[0]['Employee'] == 'A' and r.iloc[0]['Priority'] == 'High' and r.iloc[0]['Deadline'] == 'Friday'
    assert 'python' in r.iloc[0]['Reasoning'].lower()


def test_wf010_metrics_errors_slow_steps_and_recommendations():
    df = pd.DataFrame({'Workflow ID': ['W1', 'W1', 'W2', 'W2'], 'Execution Status': ['Failed', 'Success', 'Success', 'Success'],
                       'Execution Time': [100, 90, 5, 5], 'Error': ['timeout', None, None, None], 'Step': ['load', 'load', 'save', 'save']})
    r = bt.performance_report({'Execution_Logs': df}, {'percent_threshold': 10.0, 'time_threshold_seconds': 60})
    m = r['metrics'].set_index('Workflow ID')
    assert m.loc['W1', 'Flagged'] and not m.loc['W2', 'Flagged'] and m.loc['W1', 'Avg Execution Time (s)'] == 95
    assert r['frequent_errors'].iloc[0]['Error'] == 'timeout' and r['slow_steps'].iloc[0]['Step'] == 'load'
    assert any('timeout' in x for x in r['recommendations'])
