import re
import pandas as pd

WORKFLOW_NAMES = {
    'WF001':'Inventory Restock Check','WF002':'Product Price Validation','WF003':'Vendor File Processing',
    'WF004':'Product Description Generator','WF005':'Customer Order Status','WF006':'Duplicate Product Detection',
    'WF007':'Marketing Campaign Brief','WF008':'SEO Keyword Classification','WF009':'Employee Task Assignment',
    'WF010':'Workflow Performance Report'
}

def _norm(s):
    return re.sub(r'[^a-z0-9]+','_',str(s).strip().lower()).strip('_')

def _all_columns(data):
    cols=[]
    for name, df in data.items():
        cols.extend((_norm(c) for c in df.columns))
    return set(cols)

def _score(cols, required=(), optional=()):
    score=0
    for group in required:
        if any(x in cols for x in group): score += 4
        else: return -100
    for group in optional:
        if any(x in cols for x in group): score += 1
    return score

def infer_workflow(data, filename='', request=''):
    cols=_all_columns(data)
    name=_norm(filename)
    text=_norm(request)
    scores={wid:0 for wid in WORKFLOW_NAMES}
    scores['WF001']=_score(cols,[('current_stock','stock'),('minimum_stock','minimum_stock_threshold','min_stock')],[('product','product_name','sku')])
    scores['WF002']=_score(cols,[('vendor_price','supplier_price'),('internal_price','price','product_price')],[('sku',),('product','product_name')])
    scores['WF003']=_score(cols,[('vendor','vendor_name','supplier'),('product','product_name')],[('sku',),('vendor_price','supplier_price')])
    if any('vendor' in _norm(k) or 'supplier' in _norm(k) for k in data): scores['WF003'] += 8
    scores['WF004']=_score(cols,[('product','product_name')],[('category',),('attributes','features'),('material',),('color',),('target_audience','audience')])
    scores['WF005']=_score(cols,[('order_id','order_number')],[('customer_email','email'),('status','order_status'),('customer','customer_name')])
    scores['WF006']=_score(cols,[('product','product_name')],[('sku',),('description',),('category',),('material',),('color',)])
    scores['WF007']=_score(cols,[('campaign_goal','goal')],[('product_list','products'),('target_audience','audience'),('promotion','offer'),('start_date',),('end_date',)])
    scores['WF008']=_score(cols,[('keyword','keywords')],[('target_page','page'),('category','product_category'),('product','product_name')])
    scores['WF009']=_score(cols,[('employee','employee_name','name'),('skills','skill'),('workload','current_workload')],[('task','task_description'),('priority',),('deadline',)])
    scores['WF010']=_score(cols,[('workflow_id','workflow')],[('execution_status','status'),('execution_time','duration'),('error','error_message')])
    # Filename/request hints break ties and help sparse inputs.
    hints={'WF001':['inventory','stock','restock'],'WF002':['price','vendor_price','pricing'],'WF003':['vendor','supplier'],'WF004':['description','product_content','seo_content'],'WF005':['order','customer'],'WF006':['catalog','duplicate','products'],'WF007':['campaign','marketing'],'WF008':['keyword','seo'],'WF009':['employee','task','assignment'],'WF010':['execution','log','performance']}
    for wid, hs in hints.items():
        scores[wid]+=sum(3 for h in hs if h in name or h in text)
    # Explicit file/sheet naming is strong evidence when column schemas are sparse.
    if 'vendor' in name or 'supplier' in name or 'vendor' in text or 'supplier' in text: scores['WF003'] += 120
    if 'catalog' in name or 'duplicate' in name: scores['WF006'] += 12
    if 'product_content' in name or 'description' in name: scores['WF004'] += 12
    if 'campaign' in name: scores['WF007'] += 12
    if 'keyword' in name: scores['WF008'] += 12
    if 'employee' in name or 'task' in name: scores['WF009'] += 12
    if 'execution' in name or 'log' in name: scores['WF010'] += 12
    best=max(scores,key=scores.get)
    ranked=sorted(scores.items(),key=lambda x:x[1],reverse=True)
    # Require meaningful evidence; otherwise ask for a clearer file rather than guessing.
    if scores[best] <= 0:
        raise ValueError('I could not identify the workflow from this file. Please upload a business-data CSV/XLSX containing recognizable columns, or include a short description of the task.')
    return best, scores, ranked
