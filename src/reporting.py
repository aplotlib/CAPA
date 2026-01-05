# src/reporting.py
from __future__ import annotations
import pandas as pd

def export_reports(rows: list[dict], base_path: str) -> tuple[str, str]:
    df = pd.DataFrame(rows)
    csv_path = f"{base_path}.csv"
    xlsx_path = f"{base_path}.xlsx"

    df.to_csv(csv_path, index=False)

    # simple Excel writer; you can add conditional formatting later
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="Findings", index=False)

        if "LLM_relation" in df.columns:
            summary = (
                df.groupby(["SKU","Product Name","LLM_relation","LLM_severity"])
                  .size()
                  .reset_index(name="count")
                  .sort_values(["count"], ascending=False)
            )
            summary.to_excel(w, sheet_name="Summary", index=False)

    return csv_path, xlsx_path
