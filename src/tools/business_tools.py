import re
from difflib import SequenceMatcher
import pandas as pd
from src.engine.conditions import compare
from src.engine.rules import DEFAULT_TIME_THRESHOLD_SECONDS

# Fallbacks used only when the Excel Decision_Logic cell has no number.
DEFAULT_PRICE_THRESHOLD_PCT = 10.0
DEFAULT_FAILURE_RATE_PCT = 10.0
DEFAULT_MAX_WORKLOAD = 10

# Skill words recognised in a task request even if no employee has them
# (needed so the agent can escalate instead of ignoring the requirement).
COMMON_SKILLS = {'python','java','javascript','typescript','sql','react','angular','vue','node','django','flask','php','c++','c#','go','rust',
                 'frontend','backend','fullstack','devops','testing','qa','design','ui','ux','data','ml','ai','apis','api','cloud','security','mobile','android','ios'}

ALIASES = {
    'product':['product','product_name','name','item','item_name','product title'],
    'sku':['sku','product_sku','product code','item code','item sku'],
    'current_stock':['current_stock','current stock','stock','available_stock','quantity'],
    'minimum_stock':['minimum_stock','minimum stock','min_stock','reorder_level','threshold'],
    'vendor_price':['vendor_price','vendor price','supplier_price','supplier price'],
    'internal_price':['internal_price','internal price','our_price','company_price','price'],
    'order_id':['order_id','order id','order_number','order no','order_no'],
    'status':['status','order_status','shipment_status'], 'tracking_id':['tracking_id','tracking id','tracking_number','tracking number'],
    'description':['description','product_description'], 'short_description':['short_description','short description'],
    'seo_title':['seo_title','seo title'], 'meta_description':['meta_description','meta description'],
    'category':['category','product_category'], 'material':['material'], 'color':['color','colour'], 'audience':['target_audience','target audience','audience'],
    'attributes':['attributes','features','product_attributes'], 'keyword':['keyword','keywords','search_term','search query'],
    'customer_email':['customer_email','customer email','email'], 'target_page':['target_page','target page','page','url'], 'employee':['employee','employee_name','name','developer'],
    'skills':['skills','skill','expertise'], 'workload':['workload','current_workload','active_tasks','tasks'], 'task':['task','task_name','title','task requirements'],
    'max_workload':['max_workload','capacity','max_tasks','max_capacity'],
    'campaign_goal':['campaign_goal','campaign goal','goal'], 'start_date':['start_date','start date','campaign_start'], 'end_date':['end_date','end date','campaign_end'],
    'promotion':['promotion','offer','discount'], 'product_list':['product_list','products','product list'],
    'workflow_id':['workflow_id','workflow id'], 'execution_status':['execution_status','execution status','result','status'],
    'execution_time':['execution_time','execution time','duration','duration_seconds'], 'error':['error','error_message','failure_reason'],
    'step':['step','step_name','failed_step','slow_step'],
}

def norm(s): return re.sub(r'[^a-z0-9]+','_',str(s).strip().lower()).strip('_')

def find_col(df, logical):
    normalized={norm(c):c for c in df.columns}
    for alias in ALIASES.get(logical,[logical]):
        if norm(alias) in normalized: return normalized[norm(alias)]
    return None

def choose_sheet(data, preferred):
    for s in data:
        if norm(s)==norm(preferred): return data[s]
    for s in data:
        if norm(preferred) in norm(s): return data[s]
    # A CSV contains one dataset and has no sheet name. If it is the only
    # supplied dataset, use it for whichever workflow the user selected.
    if len(data) == 1:
        only = next(iter(data.values()))
        if isinstance(only, pd.DataFrame): return only
    return pd.DataFrame()

def _sheet_by_name(data, name):
    """Return a sheet only when its name really matches (no single-CSV fallback)."""
    for s in data:
        if norm(name) in norm(s): return data[s]
    return None

def required_columns(df, logicals): return {x:find_col(df,x) for x in logicals}

def _blank(v): return pd.isna(v) or str(v).strip()==''

def _text(r,c):
    return '' if not c or pd.isna(r[c]) else str(r[c]).strip()

def _trim(text, limit):
    text=' '.join(str(text).split())
    if len(text)<=limit: return text
    return text[:limit-3].rsplit(' ',1)[0].rstrip(' ,;:-')+'...'

# ---------------------------------------------------------------- WF001
def inventory_restock(data, threshold=None, rules=None):
    df=choose_sheet(data,'Inventory').copy()
    c=required_columns(df,['product','current_stock','minimum_stock'])
    if threshold is not None:                      # explicit threshold from the user's request wins
        df['_minimum_stock_threshold']=float(threshold); c['minimum_stock']='_minimum_stock_threshold'
    missing=[k for k,v in c.items() if not v]
    if missing: raise ValueError(f'Inventory data is missing columns for: {missing}')
    rows=[]
    for _,r in df.iterrows():
        if pd.isna(r[c['current_stock']]) or pd.isna(r[c['minimum_stock']]): continue
        cur=float(r[c['current_stock']]); mn=float(r[c['minimum_stock']])
        if compare(cur,'<',mn):                    # Decision_Logic: current_stock < minimum_stock
            rows.append({'Product':r[c['product']],'Current Stock':cur,'Minimum Stock':mn,'Reorder Quantity':mn-cur})
    return pd.DataFrame(rows,columns=['Product','Current Stock','Minimum Stock','Reorder Quantity'])

# ---------------------------------------------------------------- WF002
def price_validation(data, rules=None):
    threshold=float((rules or {}).get('percent_threshold',DEFAULT_PRICE_THRESHOLD_PCT))   # read from Excel
    df=choose_sheet(data,'Products').copy()
    c=required_columns(df,['sku','product','vendor_price','internal_price'])
    if not c['vendor_price']:
        vendor_sheet=next((data[k] for k in data if 'vendor' in norm(k) and 'price' in norm(k)),None)
        if vendor_sheet is not None:
            v=vendor_sheet.copy(); vc=required_columns(v,['sku','vendor_price','product'])
            key_df,key_v=(c['sku'],vc['sku']) if c['sku'] and vc['sku'] else (c['product'],vc['product'])
            if key_df and key_v and vc['vendor_price']:
                v2=v[[key_v,vc['vendor_price']]].rename(columns={key_v:key_df,vc['vendor_price']:'_vendor_price'}).drop_duplicates(subset=key_df)
                df=df.merge(v2,on=key_df,how='left'); c['vendor_price']='_vendor_price'
    missing=[k for k in ['product','vendor_price','internal_price'] if not c[k]]
    if missing: raise ValueError(f'Product data is missing columns for: {missing}')
    basis='SKU' if c['sku'] else 'Product name (no SKU column found)'
    rows=[]
    for _,r in df.iterrows():
        if pd.isna(r[c['vendor_price']]) or pd.isna(r[c['internal_price']]): continue
        vp=float(r[c['vendor_price']]); ip=float(r[c['internal_price']])
        if ip==0: continue
        diff=abs(vp-ip)/abs(ip)*100
        rows.append({'SKU':r[c['sku']] if c['sku'] else '','Product':r[c['product']],'Vendor Price':vp,'Internal Price':ip,
                     'Difference %':round(diff,2),'Exception':bool(compare(diff,'>',threshold)),'Match Basis':basis})
    return pd.DataFrame(rows)

# ---------------------------------------------------------------- WF003
def vendor_validation(data, rules=None):
    df=choose_sheet(data,'Vendors').copy(); c=required_columns(df,['sku','product'])
    if not c['product']: raise ValueError('Vendor data is missing a Product name column')
    required=[k for k in ['sku','product'] if c[k]]          # Decision_Logic: missing SKU or product name = invalid
    warnings=[]
    if not c['sku']: warnings.append('No SKU column was detected, so only the product name could be validated.')
    invalid=[]; valid_mask=[]
    for idx,r in df.iterrows():
        bad=[k for k in required if _blank(r[c[k]])]
        valid_mask.append(not bad)
        if bad: invalid.append({'Excel Row':idx+2,'Missing Fields':', '.join(bad)})
    clean=df.loc[valid_mask].reset_index(drop=True)
    renamed={col:norm(col) for col in clean.columns}        # "normalize column names" step
    clean=clean.rename(columns=renamed)
    summary={'total_rows':len(df),'valid_rows':int(sum(valid_mask)),'invalid_rows':len(invalid),
             'columns_normalized':{k:v for k,v in renamed.items() if k!=v},'warnings':warnings}
    return {'cleaned_data':clean,'invalid_rows':pd.DataFrame(invalid,columns=['Excel Row','Missing Fields']),'validation_summary':summary}

# ---------------------------------------------------------------- WF004
def description_generator(data, rules=None):
    df=choose_sheet(data,'Products').copy(); c=required_columns(df,['product','category','attributes','material','color','audience','description'])
    if not c['product']: raise ValueError('Product data is missing a Product column')
    rows=[]
    for _,r in df.iterrows():
        name=_text(r,c['product']); p={k:_text(r,c[k]) for k in ['category','attributes','material','color','audience']}
        missing=[k for k,v in p.items() if not v]
        base=_text(r,c['description'])
        if base:
            description=base
        else:                                              # only facts that were actually provided are used
            parts=[f"{name} is a {p['category'].lower()} product." if p['category'] else f'{name}.']
            if p['attributes']: parts.append(f"Key features: {p['attributes']}.")
            if p['material']: parts.append(f"Made from {p['material']}.")
            if p['color']: parts.append(f"Available in {p['color']}.")
            if p['audience']: parts.append(f"Designed for {p['audience']}.")
            description=' '.join(parts)
        first=re.split(r'(?<=[.!?])\s',description)[0]
        short=_trim(first if len(first)<=150 else description,150)
        seo_title=_trim(f"{name} | {p['category']}" if p['category'] else name,60)
        rows.append({'Product':name,'Product Description':description,'Short Description':short,'SEO Title':seo_title,
                     'Meta Description':_trim(description,155),
                     'Missing Information':', '.join(missing) if missing else 'None',
                     'Status':'Complete' if not missing else 'Incomplete - missing details were NOT invented'})
    return pd.DataFrame(rows)

# ---------------------------------------------------------------- WF005
def order_status(data, order_id=None, rules=None):
    df=choose_sheet(data,'Orders').copy(); oid=find_col(df,'order_id')
    if not oid: raise ValueError('Orders data is missing an Order ID column')
    if not order_id: return {'status':'needs_input','message':'Please provide an order ID or customer email.'}
    if '@' in str(order_id):
        email=find_col(df,'customer_email')
        mask=df[email].astype(str).str.lower()==str(order_id).lower() if email else pd.Series(False,index=df.index)
    else:
        mask=df[oid].astype(str).str.upper()==str(order_id).upper()
    found=df[mask].reset_index(drop=True)
    if found.empty: return {'status':'needs_input','message':f'No order was found for {order_id}. Please provide another identifier.'}
    order=found.to_dict(orient='records')[0]
    st=find_col(df,'status'); tr=find_col(df,'tracking_id')
    tracking='' if not tr or pd.isna(order.get(tr)) else str(order[tr])
    summary=f"Order {order[oid]} is {order[st] if st else 'in the system'}. "+(f'Tracking: {tracking}.' if tracking else 'No tracking information is available yet.')
    return {'status':'success','order':order,'summary':summary}

# ---------------------------------------------------------------- WF006
def _sim(a,b): return SequenceMatcher(None,norm(a),norm(b)).ratio()

def duplicate_products(data, rules=None):
    df=choose_sheet(data,'Products').copy().reset_index(drop=True); p=find_col(df,'product'); sku=find_col(df,'sku')
    if not p: raise ValueError('Product data is missing a Product column')
    attr_cols=[x for x in [find_col(df,'description'),find_col(df,'category'),find_col(df,'material'),find_col(df,'color')] if x]
    parent=list(range(len(df)))
    def find(x):
        while parent[x]!=x: parent[x]=parent[parent[x]]; x=parent[x]
        return x
    pairs=[]
    for i in range(len(df)):
        for j in range(i+1,len(df)):
            a,b=df.iloc[i],df.iloc[j]
            sku_match=bool(sku and not _blank(a[sku]) and not _blank(b[sku]) and norm(a[sku])==norm(b[sku]))   # blanks never match
            name_score=_sim(a[p],b[p])
            attr_scores=[_sim(str(a[x]),str(b[x])) for x in attr_cols if not pd.isna(a[x]) and not pd.isna(b[x])]
            attr_score=sum(attr_scores)/len(attr_scores) if attr_scores else name_score
            confidence='Definite' if sku_match else ('Possible' if max(name_score,attr_score)>=0.82 else None)
            if confidence:
                parent[find(i)]=find(j)
                pairs.append((i,{'Product A':a[p],'Product B':b[p],'SKU Match':sku_match,'Name Similarity %':round(name_score*100,1),
                                 'Attribute Similarity %':round(attr_score*100,1),'Confidence':confidence,
                                 'Match Reason':'Exact SKU match' if sku_match else 'High name/attribute similarity'}))
    ids={}; rows=[]
    for i,row in pairs:
        root=find(i); ids.setdefault(root,f'G{len(ids)+1}')
        rows.append({'Group ID':ids[root],**row})
    cols=['Group ID','Product A','Product B','SKU Match','Name Similarity %','Attribute Similarity %','Confidence','Match Reason']
    return pd.DataFrame(rows,columns=cols)

# ---------------------------------------------------------------- WF007
def campaign_brief(data, request='', rules=None):
    df=choose_sheet(data,'Campaign').copy(); c=required_columns(df,['campaign_goal','start_date','end_date','promotion','audience','product_list'])
    missing=[]
    for k in ['campaign_goal','start_date','end_date']:
        if not c[k] or df.empty or df[c[k]].dropna().empty: missing.append(k.replace('_',' '))
    if missing: return {'status':'needs_input','message':'Please provide: '+', '.join(missing)+'.'}
    r=df.iloc[0]; goal=_text(r,c['campaign_goal']); audience=_text(r,c['audience']) or 'Target audience to be defined'; promo=_text(r,c['promotion']) or 'Promotion to be defined'
    products=[x.strip() for x in re.split(r'[;,]',_text(r,c['product_list'])) if x.strip()]
    prod_sheet=_sheet_by_name(data,'Products')
    if not products and prod_sheet is not None:
        pc=find_col(prod_sheet,'product')
        if pc: products=[str(x) for x in prod_sheet[pc].dropna().tolist()]
    shown=', '.join(products[:5])+(f' and {len(products)-5} more' if len(products)>5 else '')
    start=pd.to_datetime(r[c['start_date']],errors='coerce'); end=pd.to_datetime(r[c['end_date']],errors='coerce')
    days=int((end-start).days)+1 if pd.notna(start) and pd.notna(end) else None
    timeline=[f"Prepare: before {r[c['start_date']]}",f"Launch: {r[c['start_date']]}",
              f"Run: until {r[c['end_date']]}"+(f' ({days} days)' if days else ''),'Review results: after campaign end']
    return {'status':'success','objective':goal,'audience':audience,'promotion':promo,'products':products or ['No product list provided'],
            'start_date':str(r[c['start_date']]),'end_date':str(r[c['end_date']]),'timeline':timeline,
            'messaging':f"{goal}."+(f' Featured products: {shown}.' if products else '')+f' Offer: {promo}.',
            'channels':['Email','Social media','Website/landing page'],
            'checklist':['Finalize creative','Confirm audience','Set tracking/metrics','Schedule launch','Monitor performance']}

# ---------------------------------------------------------------- WF008
INTENT_RULES=[
    ('transactional',['buy','price','deal','order','purchase','discount','cheap','coupon','sale','shop']),
    ('informational',['how','what','why','guide','tutorial','tips','ideas','learn','meaning']),
    ('commercial',['best','top','review','reviews','compare','vs','versus','alternative','alternatives']),
    ('navigational',['login','sign in','official','website','near me','contact','.com']),
]
PRIORITY={'transactional':'High','commercial':'Medium','informational':'Low','navigational':'Low'}
STOPWORDS={'a','an','the','to','for','of','and','in','on','best','buy','how','what','with','online'}

def _tokens(s): return set(re.findall(r'[a-z0-9]+',str(s).lower()))-STOPWORDS

def _classify_intent(keyword):
    low=keyword.lower(); toks=set(re.findall(r'[a-z0-9]+',low))
    for intent,words in INTENT_RULES:
        for w in words:
            if (' ' in w or '.' in w) and w in low: return intent,w
            if w in toks: return intent,w
    return 'commercial','default (no trigger word found)'

def keyword_classification(data, rules=None):
    df=choose_sheet(data,'Keywords').copy(); k=find_col(df,'keyword'); p=find_col(df,'target_page'); cat=find_col(df,'category')
    if not k: raise ValueError('Keyword data is missing a Keyword column')
    catalog=[]
    prod=_sheet_by_name(data,'Products')
    if prod is not None and find_col(prod,'product'):
        pc=find_col(prod,'product'); cc=find_col(prod,'category')
        for _,r in prod.iterrows():
            label=_text(r,cc) or _text(r,pc)
            if label: catalog.append((label,_tokens(_text(r,pc)+' '+_text(r,cc))))
    seen=set(); rows=[]; removed=0
    for _,r in df.iterrows():
        kw=_text(r,k)
        if not kw: continue
        if norm(kw) in seen: removed+=1; continue            # step: remove duplicates
        seen.add(norm(kw))
        intent,rule=_classify_intent(kw)
        category=_text(r,cat)
        if not category:
            kt=_tokens(kw); best=max(catalog,key=lambda x:len(x[1]&kt),default=None)
            category=best[0] if best and best[1]&kt else 'Uncategorized'
        page=_text(r,p) or (f"/{norm(category).replace('_','-')} (suggested)" if category!='Uncategorized' else '')
        rows.append({'Keyword':kw,'Intent':intent,'Category':category,'Priority':PRIORITY[intent],'Recommended Target Page':page,'Matched Rule':rule})
    out=pd.DataFrame(rows,columns=['Keyword','Intent','Category','Priority','Recommended Target Page','Matched Rule'])
    out['_o']=out['Priority'].map({'High':0,'Medium':1,'Low':2}); out=out.sort_values('_o',kind='stable').drop(columns='_o').reset_index(drop=True)
    out.attrs['duplicates_removed']=removed
    return out

# ---------------------------------------------------------------- WF009
def task_assignment(data, request='', rules=None):
    df=choose_sheet(data,'Employees').copy(); e=find_col(df,'employee'); s=find_col(df,'skills'); w=find_col(df,'workload'); cap=find_col(df,'max_workload')
    if not e or not s or not w: raise ValueError('Employee data needs Employee, Skills and Workload columns')
    task_match=re.search(r'(?:assign|task)(?: this)?\s+(.*?)(?:\s+to\s+|$)',request,re.I); task=task_match.group(1).strip() if task_match else request.strip() or 'requested task'
    low=request.lower()
    split=lambda text:[x.strip().lower() for x in re.split(r'[,;/]',str(text)) if x.strip()]
    vocabulary={sk for _,r in df.iterrows() for sk in split(r[s])}|COMMON_SKILLS
    required=sorted(sk for sk in vocabulary if re.search(r'(?<![a-z0-9])'+re.escape(sk)+r'(?![a-z0-9])',low))
    priority='High' if re.search(r'\b(urgent|critical|asap|high priority)\b',low) else ('Low' if 'low priority' in low else 'Normal (not specified)')
    dl=re.search(r'\b(?:by|before|due|deadline(?: is)?)\s+([A-Za-z0-9][A-Za-z0-9 ,/\-]*?)(?=\s+to\s|[.?!]|$)',request,re.I) or re.search(r'\b(within\s+\d+\s+(?:hours?|days?|weeks?))',request,re.I)
    deadline=dl.group(1).strip() if dl else 'Not specified'
    rows=[]
    for _,r in df.iterrows():
        skills=split(r[s]); hits=[x for x in required if x in skills]; workload=float(r[w])
        limit=float(r[cap]) if cap and not pd.isna(r[cap]) else float(DEFAULT_MAX_WORKLOAD)
        skill_ok=(not required) or bool(hits); available=compare(workload,'<',limit)
        qualifies=skill_ok and available
        score=(len(hits)*100)+((1/(1+workload))*50 if available else 0)
        rows.append({'Employee':r[e],'Skills':r[s],'Workload':workload,'Capacity Limit':limit,'Matched Skills':', '.join(hits) if hits else '-',
                     'Skill Match':len(hits),'Available':available,'Qualifies':qualifies,'Score':round(score,2)})
    ranked=pd.DataFrame(rows).sort_values(['Score','Workload'],ascending=[False,True]).reset_index(drop=True)
    good=ranked[ranked['Qualifies']]
    if good.empty:                                           # Decision_Logic: escalate if no suitable employee exists
        why=[]
        if required and not ranked['Skill Match'].gt(0).any(): why.append('nobody has the required skill(s): '+', '.join(required))
        if not ranked['Available'].any(): why.append('nobody has spare capacity')
        if not why: why.append('no employee has both the required skill and spare capacity')
        return {'status':'escalate','message':'No suitable employee found ('+'; '.join(why)+'). Escalate to the manager.','task':task,'priority':priority,'deadline':deadline}
    top=good.head(1).copy()
    r0=top.iloc[0]
    reason=((f"Has required skill(s): {r0['Matched Skills']}. " if required else 'No specific skill requirement was detected in the request, so candidates were ranked by lowest workload. ')
            +f"Workload {r0['Workload']:g} is under the capacity limit of {r0['Capacity Limit']:g}.")
    top['Reasoning']=reason; top['Priority']=priority; top['Deadline']=deadline; top['Task']=task
    return top.drop(columns=['Qualifies']).reset_index(drop=True)

# ---------------------------------------------------------------- WF010
FAILED={'failed','failure','error'}

def performance_report(data, rules=None):
    rules=rules or {}
    fail_thr=float(rules.get('percent_threshold',DEFAULT_FAILURE_RATE_PCT))                 # read from Excel Decision_Logic
    time_thr=float(rules.get('time_threshold_seconds',DEFAULT_TIME_THRESHOLD_SECONDS))
    df=choose_sheet(data,'Execution_Logs').copy(); wid=find_col(df,'workflow_id'); st=find_col(df,'execution_status')
    tm=find_col(df,'execution_time'); er=find_col(df,'error'); sp=find_col(df,'step')
    if not wid or not st: raise ValueError('Execution_Logs needs Workflow ID and Execution Status columns')
    df['_failed']=df[st].astype(str).str.lower().isin(FAILED)
    if tm: df['_time']=pd.to_numeric(df[tm],errors='coerce')
    g=df.groupby(wid)
    m=pd.DataFrame({'Total Executions':g.size(),'Failures':g['_failed'].sum().astype(int)})
    m['Failure Rate %']=(m['Failures']/m['Total Executions']*100).round(2)
    if tm: m['Avg Execution Time (s)']=g['_time'].mean().round(2)
    problems=[]; flagged=[]; reasons=[]
    for wf,r in m.iterrows():
        why=[]
        if compare(r['Failure Rate %'],'>',fail_thr): why.append(f"failure rate {r['Failure Rate %']:g}% is above {fail_thr:g}%")
        if tm and pd.notna(r['Avg Execution Time (s)']) and compare(r['Avg Execution Time (s)'],'>',time_thr):
            why.append(f"average time {r['Avg Execution Time (s)']:g}s is above {time_thr:g}s")
        flagged.append(bool(why)); reasons.append('; '.join(why))
        if why: problems.append(f'{wf}: '+'; '.join(why))
    m['Flagged']=flagged; m['Flag Reason']=reasons
    m=m.reset_index(names='Workflow ID').sort_values(['Failures','Failure Rate %'],ascending=False).reset_index(drop=True)
    errors=pd.DataFrame(columns=['Workflow ID','Error','Count'])
    if er:
        f=df[df['_failed']&df[er].notna()]
        if not f.empty:
            errors=f.groupby([wid,er]).size().reset_index(name='Count').rename(columns={wid:'Workflow ID',er:'Error'}).sort_values('Count',ascending=False).reset_index(drop=True)
    slow=pd.DataFrame(columns=['Step','Avg Time (s)','Runs'])
    if sp and tm:
        slow=df.groupby(sp)['_time'].agg(['mean','count']).reset_index().rename(columns={sp:'Step','mean':'Avg Time (s)','count':'Runs'})
        slow['Avg Time (s)']=slow['Avg Time (s)'].round(2); slow=slow.sort_values('Avg Time (s)',ascending=False).head(5).reset_index(drop=True)
    notes=[]
    if not tm: notes.append('No execution-time column found, so the average-time check was skipped.')
    if not er: notes.append('No error column found, so frequent errors could not be listed.')
    if not (sp and tm): notes.append('No step/time columns found, so slow steps could not be identified.')
    recs=[]
    for wf,why in zip(m['Workflow ID'],m['Flag Reason']):
        if not why: continue
        top=errors[errors['Workflow ID']==wf]
        extra=f" Most frequent error: '{top.iloc[0]['Error']}' ({int(top.iloc[0]['Count'])}x)." if not top.empty else ''
        recs.append(f'Review {wf} ({why}).{extra}')
    if not slow.empty and compare(slow.iloc[0]['Avg Time (s)'],'>',time_thr): recs.append(f"Optimise step '{slow.iloc[0]['Step']}' (slowest, {slow.iloc[0]['Avg Time (s)']:g}s on average).")
    if not recs: recs.append('No workflow exceeds the failure-rate or execution-time thresholds.')
    return {'status':'success','thresholds':{'failure_rate_%':fail_thr,'avg_time_seconds':time_thr},'metrics':m,'frequent_errors':errors,
            'slow_steps':slow,'problem_areas':problems,'recommendations':recs,'notes':notes}
