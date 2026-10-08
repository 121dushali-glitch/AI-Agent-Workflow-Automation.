import streamlit as st
import pandas as pd
from dotenv import load_dotenv
load_dotenv()
from src.main import build_agent
from src.workflow.excel_parser import load_business_data

st.set_page_config(page_title='AI Agent Workflow Automation', layout='wide')
st.title('AI Agent Workflow Automation')
st.caption('Upload your business data. The system automatically identifies the applicable workflow and executes it.')

upload=st.file_uploader('Upload input data', type=['csv','xlsx','xls'], help='The client does not need to choose a workflow. Upload the file and the agent will infer the workflow from its contents.')
request=st.text_input('Optional additional instruction', placeholder='Leave blank if the uploaded file contains everything needed.')


def render_result(result,key='r'):
    """Show any workflow result: tables, lists, text and status messages."""
    if isinstance(result,pd.DataFrame):
        if result.empty: st.info('Workflow completed. No matching records were found.')
        else:
            st.dataframe(result,use_container_width=True)
            st.download_button('Download as CSV',result.to_csv(index=False).encode('utf-8'),file_name=f'{key}.csv',mime='text/csv',key=f'dl_{key}')
    elif isinstance(result,dict):
        status=result.get('status')
        if status=='needs_input': st.warning(result['message']); return
        if status=='escalate': st.error(result['message']); return
        for name,value in result.items():
            if name=='status': continue
            label=name.replace('_',' ').title()
            if isinstance(value,(pd.DataFrame,list,dict)) and not (hasattr(value,'__len__') and len(value)==0):
                st.markdown(f'**{label}**')
                if isinstance(value,pd.DataFrame): render_result(value,f'{key}_{name}')
                elif isinstance(value,list):
                    for item in value: st.write(f'- {item}')
                else: st.json(value)
            elif isinstance(value,(pd.DataFrame,list,dict)): continue
            else: st.write(f'**{label}:** {value}')
    else: st.write(result)

data={}
if upload:
    try:
        data=load_business_data(upload)
        total=sum(len(df) for df in data.values())
        st.success(f'Loaded {total} rows across {len(data)} dataset(s) from {upload.name}.')
        with st.expander('Preview uploaded data', expanded=True):
            for name,df in data.items():
                st.write(f'**{name}** — {len(df)} rows × {len(df.columns)} columns')
                st.dataframe(df.head(10),use_container_width=True)
    except Exception as e:
        st.error(f'Could not read this file: {e}')

if st.button('Analyze & Run Automatically',type='primary',disabled=not data):
    try:
        with st.spinner('Inspecting the uploaded data, selecting the workflow, and executing it...'):
            workflow,result,ctx=build_agent()(request,data,upload.name)
        st.subheader('Automatically Selected Workflow')
        st.success(f"{workflow['Workflow_ID']} — {workflow['Workflow_Name']}")
        source=getattr(ctx,'selection_source','fallback')
        confidence=getattr(ctx,'selection_confidence',0)
        reason=getattr(ctx,'selection_reason','')
        st.caption(f"Selection source: {source} | Confidence: {confidence:.0%}")
        if reason: st.info(reason)
        scores=getattr(ctx,'auto_detection_scores',{})
        if scores:
            ranked=sorted(scores.items(),key=lambda x:x[1],reverse=True)[:3]
            st.caption('Detection confidence scores: '+', '.join(f'{w}={s}' for w,s in ranked))
        st.subheader('Execution Trace')
        for item in ctx.trace:
            icon='✅' if item['status']=='success' else '❌'
            st.write(f"{icon} {item['step']}"+(f" — {item['details']}" if item['details'] else ''))
        st.subheader('Final Result')
        render_result(result)
    except Exception as e:
        st.error(f'Workflow could not be completed: {e}')

with st.expander('How automatic workflow selection works'):
    st.markdown('''The client does not select WF001–WF010. The agent inspects sheet names, column names, and the optional instruction, then chooses the best matching workflow. CSV is treated as one dataset; XLS/XLSX can contain multiple sheets. If the data is genuinely ambiguous or missing required information, the application reports what is missing instead of silently running the wrong workflow.''')
