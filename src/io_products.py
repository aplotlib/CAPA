# src/io_products.py
from __future__ import annotations
import pandas as pd

REQUIRED_COLS = ["SKU", "Product Name"]

def read_products(uploaded_file) -> pd.DataFrame:
    name = uploaded_file.name.lower()

    if name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    elif name.endswith(".xlsx") or name.endswith(".xls"):
        df = pd.read_excel(uploaded_file)
    else:
        raise ValueError("Upload must be .csv or .xlsx")

    df.columns = [c.strip() for c in df.columns]
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}. Expected headers: {REQUIRED_COLS}")

    df = df[REQUIRED_COLS].copy()
    df["SKU"] = df["SKU"].astype(str).str.strip()
    df["Product Name"] = df["Product Name"].astype(str).str.strip()
    df = df[df["SKU"].ne("") & df["Product Name"].ne("")]

    # de-dupe exact duplicates
    df = df.drop_duplicates(subset=["SKU", "Product Name"]).reset_index(drop=True)
    return df
