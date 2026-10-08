from pathlib import Path
import pandas as pd
from src.workflow.excel_parser import load_business_data
from src.tools.business_tools import inventory_restock, price_validation, keyword_classification


def test_csv_loader(tmp_path):
    path = tmp_path / "inventory.csv"
    pd.DataFrame({
        "Product": ["A", "B"],
        "Current Stock": [2, 20],
        "Minimum Stock": [5, 10],
    }).to_csv(path, index=False)
    data = load_business_data(path)
    assert list(data) == ["CSV"]
    result = inventory_restock(data)
    assert len(result) == 1
    assert result.iloc[0]["Reorder Quantity"] == 3


def test_csv_applicable_workflows_use_single_dataset():
    data = {"CSV": pd.DataFrame({
        "SKU": ["P1", "P2"],
        "Product": ["Mouse", "Keyboard"],
        "Vendor Price": [120, 200],
        "Internal Price": [100, 100],
    })}
    result = price_validation(data)
    assert result["Exception"].tolist() == [True, True]
