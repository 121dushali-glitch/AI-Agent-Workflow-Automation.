from pathlib import Path
from src.workflow.excel_parser import load_workflow_definitions
from src.workflow.registry import WorkflowRegistry
from src.agent.selector import extract_parameters, select_workflow
from src.agent.llm_selector import select_with_llm
from src.engine.context import ExecutionContext
from src.engine.engine import WorkflowEngine
from src.auto_router import infer_workflow

ROOT=Path(__file__).resolve().parents[1]
WORKFLOW_FILE=ROOT/'data'/'workflows.xlsx'


def _parameters_from_data(data):
    p={}
    for _, df in data.items():
        cols={str(c).strip().lower():c for c in df.columns}
        oid=next((cols[k] for k in ['order id','order_id','order number','order_number'] if k in cols),None)
        email=next((cols[k] for k in ['customer email','customer_email','email'] if k in cols),None)
        if oid and len(df)==1 and pd_notna(df.iloc[0][oid]): p['order_id']=str(df.iloc[0][oid])
        if email and len(df)==1 and pd_notna(df.iloc[0][email]): p['customer_email']=str(df.iloc[0][email])
    return p


def pd_notna(x):
    try:
        import pandas as pd
        return pd.notna(x)
    except Exception:
        return x is not None


def build_agent(workflow_file=WORKFLOW_FILE):
    definitions=load_workflow_definitions(workflow_file)
    registry=WorkflowRegistry(definitions)
    engine=WorkflowEngine(registry)

    def run(request='', business_data=None, filename=''):
        business_data=business_data or {}
        # Primary path: LLM chooses only from the Excel-backed registry.
        llm_choice=select_with_llm(request, registry.all(), business_data, filename)
        selection_source='llm'
        if llm_choice:
            wid, confidence, reason, _ = llm_choice
            workflow=registry.get(wid)
            scores={wid: round(confidence*100,2)}
        else:
            # Offline/test fallback: an explicit natural-language request is the
            # strongest available signal; otherwise infer from the uploaded data.
            explicit=select_workflow(request, registry.all()) if request else None
            if explicit:
                workflow=explicit
                wid=workflow['Workflow_ID']
                scores={wid:100.0}
                confidence=1.0
                reason='Selected from the user request using the Excel-backed workflow registry.'
            else:
                wid, scores, ranked=infer_workflow(business_data, filename, request)
                workflow=registry.get(wid)
                confidence=(scores[wid]/max(1.0, max(scores.values()))) if scores else 0.0
                reason='Selected from uploaded-data schema, filename and request using the registry-backed fallback.'
            selection_source='fallback'
        if not workflow:
            raise ValueError(f'Workflow {wid} is not configured in workflows.xlsx.')

        params=extract_parameters(request or '')
        params.update({k:v for k,v in _parameters_from_data(business_data).items() if k not in params})
        ctx=ExecutionContext(request=request or workflow['Workflow_Name'],workflow=workflow,data=business_data,parameters=params)
        ctx.selection_source=selection_source
        ctx.selection_confidence=confidence
        ctx.selection_reason=reason
        ctx.auto_detection_scores=scores
        result=engine.execute(ctx)
        return workflow,result,ctx
    return run
