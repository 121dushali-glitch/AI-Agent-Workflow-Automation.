import re

KEYWORDS={
'WF001':['restock','stock','inventory','reorder','low stock'], 'WF002':['vendor price','price differs','price difference','10%','price validation'],
'WF003':['vendor spreadsheet','vendor file','invalid rows','validate vendor','process vendor'], 'WF004':['description','seo content','product content','generate content'],
'WF005':['order status','where is order','shipment','tracking','order'], 'WF006':['duplicate','similar products','duplicate products','catalog'],
'WF007':['campaign brief','marketing campaign','campaign'], 'WF008':['keyword','seo keyword','classify keywords','map keywords'], 'WF009':['assign','employee','developer','urgent task','best available'], 'WF010':['performance','failing','failure','execution logs','workflow report']}

def select_workflow(request,workflows):
    text=request.lower(); scored=[]
    for w in workflows:
        wid=w['Workflow_ID']; score=sum(1 for k in KEYWORDS.get(wid,[]) if k in text)
        score += sum(0.2 for token in re.findall(r'\w+',str(w['Workflow_Name']).lower()) if len(token)>3 and token in text)
        scored.append((score,w))
    scored.sort(key=lambda x:x[0],reverse=True); return scored[0][1] if scored and scored[0][0]>0 else None

def extract_parameters(request):
    params={}
    m=re.search(r'\b(ORD[-_ ]?\d+)\b',request,re.I)
    if m: params['order_id']=m.group(1).replace(' ','-').replace('_','-').upper()
    e=re.search(r'([\w.+-]+@[\w.-]+\.[A-Za-z]{2,})', request)
    if e: params['customer_email']=e.group(1)
    t=re.search(r'(?:threshold|min(?:imum)? stock(?: threshold)?)[^0-9]*(\d+(?:\.\d+)?)', request,re.I)
    if t: params['minimum_stock_threshold']=float(t.group(1))
    return params
