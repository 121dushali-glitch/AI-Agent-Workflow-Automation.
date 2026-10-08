from pathlib import Path
from src.workflow.excel_parser import load_workflow_definitions
from src.agent.selector import select_workflow,extract_parameters
ROOT=Path(__file__).resolve().parents[1]
def test_workflow_definitions(): assert len(load_workflow_definitions(ROOT/'data'/'workflows.xlsx'))==10
def test_selector():
    ws=load_workflow_definitions(ROOT/'data'/'workflows.xlsx'); assert select_workflow('Which products need restocking?',ws)['Workflow_ID']=='WF001'; assert extract_parameters('Where is order ORD-1001?')['order_id']=='ORD-1001'
