from pathlib import Path
import pandas as pd
from src.main import build_agent
from src.workflow.excel_parser import load_business_excel
ROOT=Path(__file__).resolve().parents[1]; DATA=load_business_excel(ROOT/'data'/'sample_daily_business_data.xlsx')
CASES=[('Which products need restocking?','WF001'),('Find products where vendor price differs by more than 10%.','WF002'),('Process this vendor spreadsheet and show invalid rows.','WF003'),('Generate SEO content for this product.','WF004'),('Where is order ORD-1001?','WF005'),('Find likely duplicate products in the catalog.','WF006'),('Create a campaign brief for the new collection.','WF007'),('Classify these keywords and map them to pages.','WF008'),('Assign this urgent task to the best available developer.','WF009'),('Which workflows are failing most often?','WF010')]
def test_all_10_workflows_execute_end_to_end():
    agent=build_agent()
    for req,wid in CASES:
        workflow,result,ctx=agent(req,DATA); assert workflow['Workflow_ID']==wid; assert result is not None; assert len(ctx.trace)>=5; assert not ctx.errors
def test_inventory_changes_with_uploaded_values():
    changed={n:d.copy() for n,d in DATA.items()}; changed['Inventory'].loc[changed['Inventory']['Product']=='Mouse','Current Stock']=50
    _,result,_=build_agent()('Which products need restocking?',changed); assert 'Mouse' not in result['Product'].tolist()
def test_order_lookup():
    _,result,_=build_agent()('Where is order ORD-1002?',DATA); assert result['order']['Order ID']=='ORD-1002'
def test_vendor_returns_cleaned_and_invalid():
    _,result,_=build_agent()('Process this vendor spreadsheet and show invalid rows.',DATA); assert len(result['invalid_rows'])==1 and len(result['cleaned_data'])==2
def test_price_validation_flags_over_10_percent():
    _,result,_=build_agent()('Find products where vendor price differs by more than 10%.',DATA); assert result['Exception'].any() and result['Exception'].sum() == 3
def test_campaign_missing_dates_pauses():
    broken={n:d.copy() for n,d in DATA.items()}; broken['Campaign']=broken['Campaign'].drop(columns=['End Date']); _,result,_=build_agent()('Create a campaign brief for the new collection.',broken); assert result['status']=='needs_input'
