import pandas as pd
from src.auto_router import infer_workflow

def test_auto_routes_representative_inputs():
    cases=[
      ('inventory.csv', {'CSV':pd.DataFrame({'Product':['A'],'Current Stock':[2],'Minimum Stock':[5]})}, 'WF001'),
      ('products.csv', {'CSV':pd.DataFrame({'SKU':['A'],'Product':['A'],'Internal Price':[100],'Vendor Price':[120]})}, 'WF002'),
      ('vendor.csv', {'Vendors':pd.DataFrame({'Product':['A'],'Vendor Price':[120],'Description':['x']})}, 'WF003'),
      ('product_content.csv', {'CSV':pd.DataFrame({'Product':['A'],'Category':['Shoes'],'Attributes':['sport'],'Material':['leather'],'Color':['black'],'Target Audience':['adults']})}, 'WF004'),
      ('orders.csv', {'CSV':pd.DataFrame({'Order ID':['ORD-1'],'Status':['Shipped']})}, 'WF005'),
      ('product_catalog.csv', {'CSV':pd.DataFrame({'SKU':['A'],'Product':['A'],'Description':['x'],'Category':['Shoes']})}, 'WF006'),
      ('campaign.csv', {'CSV':pd.DataFrame({'Campaign Goal':['Launch'],'Start Date':['2026-01-01'],'End Date':['2026-01-07'],'Promotion':['10%'],'Target Audience':['Adults']})}, 'WF007'),
      ('keywords.csv', {'CSV':pd.DataFrame({'Keyword':['buy shoes'],'Target Page':['/shoes']})}, 'WF008'),
      ('employees.csv', {'CSV':pd.DataFrame({'Employee':['A'],'Skills':['python'],'Workload':[2]})}, 'WF009'),
      ('execution_logs.csv', {'CSV':pd.DataFrame({'Workflow ID':['WF001'],'Execution Status':['Failed']})}, 'WF010'),
    ]
    for fn,data,wid in cases:
        assert infer_workflow(data,fn)[0]==wid
