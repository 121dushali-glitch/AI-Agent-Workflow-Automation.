from pathlib import Path
import pandas as pd


def load_workflow_definitions(path):
    xls = pd.ExcelFile(path)
    df = pd.read_excel(path, sheet_name='Workflows').fillna('')
    required = ['Workflow_ID','Workflow_Name','Trigger','Inputs','Steps','Decision_Logic','Tools_Required','Expected_Output']
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f'workflows.xlsx is missing columns: {missing}')
    return df.to_dict('records')


def load_business_data(file_or_path):
    """Read daily business data from CSV or Excel.

    Excel files return all sheets. CSV files return one logical sheet named
    ``CSV``; workflow tools can use it automatically when only one dataset is
    supplied.
    """
    if hasattr(file_or_path, "name"):
        filename = str(file_or_path.name).lower()
    else:
        filename = str(file_or_path).lower()

    if filename.endswith(".csv"):
        if hasattr(file_or_path, "read"):
            file_or_path.seek(0)
            df = pd.read_csv(file_or_path)
        else:
            df = pd.read_csv(Path(file_or_path))
        return {"CSV": df.dropna(how="all")}

    if hasattr(file_or_path, 'read'):
        file_or_path.seek(0)
        xls = pd.ExcelFile(file_or_path)
    else:
        xls = pd.ExcelFile(Path(file_or_path))
    return {name: pd.read_excel(xls, sheet_name=name).dropna(how='all') for name in xls.sheet_names}


# Backward-compatible name used by existing callers.
load_business_excel = load_business_data
