# utils/body_parser.py
import pandas as pd
import re
import logging

logger = logging.getLogger("body_parser")

def parse_table_text_to_df(text):
    """
    Parse a table-like text into a DataFrame.
    Expected header: EMAIL   FIRST_NAME   LAST_NAME
    Rows separated by newline, columns separated by tabs or multiple spaces.
    """
    lines = [ln for ln in text.splitlines() if ln.strip() != ""]
    if not lines:
        return pd.DataFrame(columns=["EMAIL", "FIRST_NAME", "LAST_NAME"])

    # Find header line index (first line that contains EMAIL and FIRST_NAME)
    header_idx = None
    for i, ln in enumerate(lines[:5]):  # header likely in first 5 lines
        if re.search(r"\bEMAIL\b", ln, re.IGNORECASE) and re.search(r"\bFIRST_NAME\b", ln, re.IGNORECASE):
            header_idx = i
            break
    if header_idx is None:
        # assume first line is header
        header_idx = 0

    header_line = lines[header_idx]
    # Normalize header tokens
    header_tokens = re.split(r"\s{2,}|\t", header_line.strip())
    header_tokens = [t.strip().upper() for t in header_tokens if t.strip() != ""]

    # expected columns
    expected = ["EMAIL", "FIRST_NAME", "LAST_NAME"]
    # If header tokens don't match exactly, try to map first three tokens
    if header_tokens[:3] != expected:
        header_tokens = expected

    data_lines = lines[header_idx + 1 :]

    rows = []
    for ln in data_lines:
        # split on two or more spaces or tabs
        parts = re.split(r"\s{2,}|\t", ln.strip())
        # If splitting yields only one token, try splitting on single spaces but keep groups of 3
        if len(parts) == 1:
            parts = ln.strip().split()
        # pad or trim to 3 columns
        if len(parts) < 3:
            parts = parts + [""] * (3 - len(parts))
        elif len(parts) > 3:
            # If there are extra tokens, assume last tokens belong to LAST_NAME (join them)
            parts = [parts[0], parts[1], " ".join(parts[2:])]
        rows.append(parts[:3])

    df = pd.DataFrame(rows, columns=expected)
    # Normalize NULL and placeholders
    df = df.replace({"NULL": "", "null": "", "None": "", "NONE": ""})
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    # Drop rows where all columns empty
    df = df[~(df["EMAIL"].eq("") & df["FIRST_NAME"].eq("") & df["LAST_NAME"].eq(""))].reset_index(drop=True)
    return df
