import pandas as pd


def clean_labels(records):
    """Strip and lower-case the text columns, and report rows whose label was never provided.

    records: [{"name": ..., "label": ..., "score": ...}, ...]. Returns the cleaned rows, the cleaned column names and
    the positions of the rows with no label (null).
    """
    df = pd.DataFrame(records, columns=["name", "label", "score"])
    missing = [i for i, v in enumerate(df["label"]) if v is None]
    cleaned = []
    for col in df.columns:
        if df[col].dtype == object:  # text column
            df[col] = df[col].str.strip().str.lower()
            cleaned.append(col)
    rows = []
    for name, label, score in df.itertuples(index=False):
        rows.append([None if pd.isna(name) else str(name),
                     None if pd.isna(label) else str(label),
                     None if pd.isna(score) else int(score)])
    return {"cleaned": cleaned, "missing": missing, "rows": rows}
