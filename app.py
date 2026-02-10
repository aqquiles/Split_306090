import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import math
import io
import zipfile
import csv

# --- UI Setup ---
st.set_page_config(page_title="RSC | Split per lead's age", layout="wide")

st.markdown("""
    <style>
    th { color: #4e73df !important; font-weight: bold !important; }
    .stButton>button { background-color: #4e73df; color: white; border-radius: 5px; border: none; width: 100%; }
    .stAlert { border-left: 5px solid #32CD32; }
    /* Metric styling */
    [data-testid="stMetricValue"] { color: #4e73df; }
    </style>
    """, unsafe_allow_html=True)

st.title("Split per lead's age")

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("Settings")
    project_prefix = st.text_input("Project Name Prefix", value="", placeholder="e.g. mrPBall")
    date_col = st.text_input("Date Column", value="joindate")
    initial_chunk_size = st.number_input("Global Chunk Size", value=50000)
    
    st.divider()
    st.subheader("Data Enhancements")
    keep_age_col = st.toggle("Add lead age column to output", value=False)
    
    st.divider()
    st.subheader("Data Parsing")
    manual_delimiter = st.checkbox("Set delimiter manually", value=False)
    detected_sep = ","
    if manual_delimiter:
        detected_sep = st.selectbox("Select Delimiter", [",", ";", "|", "\\t"])

uploaded_file = st.file_uploader("Upload CSV to Split", type="csv")

if uploaded_file:
    # 1. Delimiter Logic
    if not manual_delimiter:
        try:
            sample = uploaded_file.read(2048).decode('utf-8')
            uploaded_file.seek(0)
            dialect = csv.Sniffer().sniff(sample, delimiters=[',', ';', '|', '\t'])
            detected_sep = dialect.delimiter
        except:
            st.error("⚠️ Auto-detection failed. Set delimiter manually in sidebar.")
            st.stop()

    # 2. Load and Process Data
    try:
        df = pd.read_csv(uploaded_file, sep=detected_sep)
        today = pd.Timestamp(2026, 2, 10) 
        
        if date_col not in df.columns:
            st.error(f"Column '{date_col}' not found.")
            st.stop()
            
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        valid_mask = df[date_col].notna()
        
        def get_bucket(age):
            if 0 <= age < 30: return "0-30_days"
            if 30 <= age < 60: return "30-60_days"
            if 60 <= age <= 90: return "60-90_days"
            return "outside_0_90"

        df.loc[valid_mask, 'age_days'] = (today - df.loc[valid_mask, date_col]).dt.days
        df.loc[valid_mask, 'bucket'] = df.loc[valid_mask, 'age_days'].apply(get_bucket)
        df.loc[~valid_mask, 'bucket'] = "invalid_date"

        # --- NEW/RESTORED: 3. Top Metrics Row ---
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Rows", f"{len(df):,}")
        col2.metric("Date Reference", today.strftime('%Y-%m-%d'))
        col3.metric("Valid Dates", f"{valid_mask.sum():,}")
        col4.metric("Delimiter", f"'{detected_sep}'")

        # 4. Generate Initial Project Data & Stats
        buckets = ["0-30_days", "30-60_days", "60-90_days", "outside_0_90", "invalid_date"]
        all_chunks_data = []
        stats_text = [f"Today: {today.strftime('%Y-%m-%d')}", f"Total rows: {len(df)}"]
        
        for b in buckets:
            group = df[df['bucket'] == b]
            row_count = len(group)
            num_chunks = math.ceil(row_count / initial_chunk_size) if row_count > 0 else 0
            stats_text.append(f"{b.replace('_',' ')}: {row_count} rows, {num_chunks} chunk(s)")
            
            if not group.empty:
                for i in range(0, row_count, initial_chunk_size):
                    chunk = group.iloc[i:i + initial_chunk_size]
                    chunk_num = (i // initial_chunk_size) + 1
                    name_parts = [project_prefix, b, f"chunk{chunk_num:03d}"]
                    chunk_name = "_".join([p for p in name_parts if p])
                    
                    all_chunks_data.append({
                        "Select": False,
                        "File Name": chunk_name,
                        "Contacts": len(chunk),
                        "Bucket": b,
                        "Override Chunk Size": initial_chunk_size,
                        "raw_data": chunk
                    })

        # --- RESTORED: 5. Summary Text Block ---
        st.code("\n".join(stats_text), language="text")

        # 6. Interactive Table
        st.subheader("Project Files Management")
        st.markdown("Select files to **sub-split** further by overriding their chunk size.")
        
        edited_df = st.data_editor(
            pd.DataFrame(all_chunks_data).drop(columns=['raw_data']),
            column_config={
                "Select": st.column_config.CheckboxColumn(label="Sub-Split?", help="Check to split this file even smaller"),
                "Override Chunk Size": st.column_config.NumberColumn(label="New Chunk Size", min_value=1, step=1000)
            },
            disabled=["File Name", "Contacts", "Bucket"],
            hide_index=True,
            use_container_width=True
        )

        # 7. Final Processing Logic
        zip_buffer = io.BytesIO()
        final_file_count = 0

        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for idx, row in edited_df.iterrows():
                original_chunk = all_chunks_data[idx]['raw_data']
                
                if row['Select']:
                    sub_chunk_size = int(row['Override Chunk Size'])
                    for j in range(0, len(original_chunk), sub_chunk_size):
                        sub_chunk = original_chunk.iloc[j:j + sub_chunk_size].copy()
                        sub_name = f"{row['File Name']}_sub{(j//sub_chunk_size)+1:02d}"
                        
                        cols_to_drop = ['bucket']
                        if not keep_age_col: cols_to_drop.append('age_days')
                        else: sub_chunk = sub_chunk.rename(columns={'age_days': 'lead_age_days'})
                        
                        csv_data = sub_chunk.drop(columns=cols_to_drop, errors='ignore').to_csv(index=False, sep=detected_sep)
                        zip_file.writestr(f"{sub_name}.csv", csv_data)
                        final_file_count += 1
                else:
                    final_chunk = original_chunk.copy()
                    cols_to_drop = ['bucket']
                    if not keep_age_col: cols_to_drop.append('age_days')
                    else: final_chunk = final_chunk.rename(columns={'age_days': 'lead_age_days'})
                    
                    csv_data = final_chunk.drop(columns=cols_to_drop, errors='ignore').to_csv(index=False, sep=detected_sep)
                    zip_file.writestr(f"{row['File Name']}.csv", csv_data)
                    final_file_count += 1

        st.success(f"Successfully processed {final_file_count} files.")

        st.download_button(
            label="Download split file (.zip)",
            data=zip_buffer.getvalue(),
            file_name=f"{project_prefix if project_prefix else 'Split'}_{today.strftime('%Y%m%d')}.zip",
            mime="application/zip"
        )
        
    except Exception as e:
        st.error(f"Error: {e}")
