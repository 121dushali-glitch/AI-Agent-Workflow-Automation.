from pathlib import Path
from src.workflow.excel_parser import load_workflow_definitions
from src.workflow.registry import WorkflowRegistry
from src.agent.llm_selector import build_selection_prompt
from src.engine.engine import WorkflowEngine

ROOT=Path(__file__).resolve().parents[1]

def test_registry_is_excel_driven_and_engine_is_generic():
    registry=WorkflowRegistry(load_workflow_definitions(ROOT/'data'/'workflows.xlsx'))
    assert len(registry.all()) == 10
    assert registry.get('WF001') is not None
    assert registry.get('WF010') is not None
    assert isinstance(WorkflowEngine(registry).tools.tools, dict)


def test_selector_prompt_contains_registry_and_uploaded_schema():
    registry=WorkflowRegistry(load_workflow_definitions(ROOT/'data'/'workflows.xlsx'))
    import pandas as pd
    prompt=build_selection_prompt('find low stock products', registry.all(), {'CSV':pd.DataFrame({'Product':['A'],'Current Stock':[2],'Minimum Stock':[5]})}, 'inventory.csv')
    assert 'WF001' in prompt
    assert 'Current Stock' in prompt
    assert 'inventory.csv' in prompt
