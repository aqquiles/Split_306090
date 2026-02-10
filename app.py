import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import math
import io
import zipfile

# --- UI Setup ---
st.set_page_config(page_title="Brightcall AI | CSV Splitter", layout="wide")

# Custom CSS for Brightcall Look
st.markdown("""
    <style>
    .main { background-color: #f8f9fc; }
    .stTable { background-color: white; border-radius: 10px; }
    div[data-testid="stMetricValue"] { color: #4e73df; }
    </style>
    """, unsafe_allow_html=True)

st.title("Projects")

# --- Configuration ---
with st.sidebar:
    st.header("Settings")
    date_col = st.text_input("Date Column", value="joindate")
    chunk_size = st.number_input("Chunk Size", value=50000)
    delimiter = st.selectbox("Delimiter", [",", ";"])

# --- App Logic ---
def get_bucket(age):
    if 0 <= age < 30: return "0-30_days"
    if 30 <= age < 60: return "30-60_days"
    if 60 <= age <= 90: return "60-90_days"
    return "outside_0_90"

uploaded_file = st.file_uploader("Upload CSV to Split", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file, sep=delimiter)
    # Use 2026-02-10 as requested
    today = pd.Timestamp(2026, 2, 10)
    
    # Process Dates
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    valid_mask = df[date_col].notna()
    
    # Calculate Buckets
    df.loc[valid_mask, 'age_days'] = (today - df.loc[valid_mask, date_col]).dt.days
    df.loc[valid_mask, 'bucket'] = df.loc[valid_mask, 'age_days'].apply(get_bucket)
    df.loc[~valid_mask, 'bucket'] = "invalid_date"

    # --- Summary Section ---
    buckets = ["0-30_days", "30-60_days", "60-90_days", "outside_0_90", "invalid_date"]
    stats = {b: {"rows": 0, "chunks": 0} for b in buckets}
    
    for b in buckets:
        row_count = len(df[df['bucket'] == b])
        stats[b]["rows"] = row_count
        stats[b]["chunks"] = math.ceil(row_count / chunk_size) if row_count > 0 else 0

    st.code(f"""
Today: {today.strftime('%Y-%m-%d')}

Total rows: {len(df)}
0-30 days:    {stats['0-30_days']['rows']} rows, {stats['0-30_days']['chunks']} chunk(s)
30-60 days:   {stats['30-60_days']['rows']} rows, {stats['30-60_days']['chunks']} chunk(s)
60-90 days:   {stats['60-90_days']['rows']} rows, {stats['60-90_days']['chunks']} chunk(s)
Outside 0-90: {stats['outside_0_90']['rows']} rows, {stats['outside_0_90']['chunks']} chunk(s)
Invalid date: {stats['invalid_date']['rows']} rows, {stats['invalid_date']['chunks']} chunk(s)
    """, language="text")

    # --- Project Table ---
    project_rows = []
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for b in buckets:
            group = df[df['bucket'] == b]
            if not group.empty:
                for i in range(0, len(group), chunk_size):
                    chunk = group.iloc[i:i + chunk_size]
                    chunk_num = i//chunk_size + 1
                    chunk_name = f"{b}_chunk{chunk_num:03d}"
                    
                    csv_data = chunk.drop(columns=['age_days', 'bucket'], errors='ignore').to_csv(index=False)
                    zip_file.writestr(f"{chunk_name}.csv", csv_data)
                    
                    project_rows.append({
                        "Project": chunk_name,
                        "Project Type": "AI Agent",
                        "Contacts Added": len(chunk),
                        "Status": "Ready"
                    })

    if project_rows:
        st.table(pd.DataFrame(project_rows))

    st.download_button(
        label="Add new project",
        data=zip_buffer.getvalue(),
        file_name=f"SplitOutput_{today.strftime('%Y%m%d')}.zip",
        mime="application/zip",
        type="primary"
    )
