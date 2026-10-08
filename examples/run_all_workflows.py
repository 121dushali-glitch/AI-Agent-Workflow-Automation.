import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pandas as pd
from src.main import build_agent
from src.workflow.excel_parser import load_business_excel
data=load_business_excel(ROOT/'data'/'sample_daily_business_data.xlsx'); questions=pd.read_excel(ROOT/'data'/'workflows.xlsx',sheet_name='Test_Questions')
for _,row in questions.iterrows():
    wf,result,ctx=build_agent()(row['Test_Request'],data); print(f"\n[{wf['Workflow_ID']}] {wf['Workflow_Name']}\nRequest: {row['Test_Request']}\nTrace: {len(ctx.trace)} steps")
    if isinstance(result,pd.DataFrame): print(result.to_string(index=False) if not result.empty else 'No matching records.')
    else: print(result)
