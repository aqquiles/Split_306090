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
    div[data-testid="stTable"] { background-color: transparent !important; }
    th { color: #4e73df !important; font-weight: bold !important; }
    .stButton>button { background-color: #4e73df; color: white; border-radius: 5px; border: none; width: 100%; }
    /* Error message styling */
    .stAlert { border-left: 5px solid #32CD32; }
    </style>
    """, unsafe_allow_html=True)

st.title("Split per lead's age")

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("Settings")
    project_prefix = st.text_input("Project Name Prefix", value="", placeholder="e.g. mrPBall")
    date_col = st.text_input("Date Column", value="joindate")
    chunk_size = st.number_input("Chunk Size", value=50000)
    
    st.divider()
    st.subheader("Data Enhancements")
    # New Toggle for adding the age column
    keep_age_col = st.toggle("Add lead age column to output", value=False, help="Adds a 'lead_age_days' column to the exported CSVs.")
    
    st.divider()
    st.subheader("Data Parsing")
    manual_delimiter = st.checkbox("Set delimiter manually", value=False)
    if manual_delimiter:
        delimiter_choice = st.selectbox("Select Delimiter", [",", ";", "|", "\\t"])
    else:
        st.info("Delimiter auto-detection is ON")

uploaded_file = st.file_uploader("Upload CSV to Split", type="csv")

if uploaded_file:
    detected_sep = None
    
    # 1. Delimiter Logic
    if manual_delimiter:
        detected_sep = delimiter_choice
    else:
        try:
            sample = uploaded_file.read(2048).decode('utf-8')
            uploaded_file.seek(0)
            dialect = csv.Sniffer().sniff(sample, delimiters=[',', ';', '|', '\t'])
            detected_sep = dialect.delimiter
        except Exception:
            st.error("⚠️ **Auto-detection failed.** We couldn't determine the delimiter for this file.")
            st.warning("Please check the **'Set delimiter manually'** box in the sidebar.")
            st.stop()

    # 2. Load Data
    try:
        df = pd.read_csv(uploaded_file, sep=detected_sep)
        today = pd.Timestamp(2026, 2, 10) 
        
        # 3. Process Dates & Buckets
        if date_col not in df.columns:
            st.error(f"Column '{date_col}' not found in the file. Current columns: {', '.join(df.columns)}")
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

        # 4. Top Metrics Row
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Rows", len(df))
        col2.metric("Date Reference", today.strftime('%Y-%m-%d'))
        col3.metric("Valid Dates", valid_mask.sum())
        col4.metric("Delimiter", f"{detected_sep}")

        # 5. Processing with Progress Bar
        buckets = ["0-30_days", "30-60_days", "60-90_days", "outside_0_90", "invalid_date"]
        stats_text = [f"Today: {today.strftime('%Y-%m-%d')}", f"Total rows: {len(df)}"]
        
        project_rows = []
        zip_buffer = io.BytesIO()
        
        progress_bar = st.progress(0)
        status_text = st.empty()

        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for idx, b in enumerate(buckets):
                status_text.text(f"Processing {b.replace('_',' ')}...")
                group = df[df['bucket'] == b]
                row_count = len(group)
                num_chunks = math.ceil(row_count / chunk_size) if row_count > 0 else 0
                
                stats_text.append(f"{b.replace('_',' ')}: {row_count} rows, {num_chunks} chunk(s)")
                
                if row_count > 0:
                    for i in range(0, row_count, chunk_size):
                        chunk = group.iloc[i:i + chunk_size].copy() # Copy to avoid slice warnings
                        chunk_num = (i//chunk_size) + 1
                        
                        name_parts = [project_prefix, b, f"chunk{chunk_num:03d}"]
                        chunk_name = "_".join([p for p in name_parts if p])
                        
                        # Logic to keep or drop columns
                        cols_to_drop = ['bucket']
                        if not keep_age_col:
                            cols_to_drop.append('age_days')
                        else:
                            # Rename for a cleaner output header
                            chunk = chunk.rename(columns={'age_days': 'lead_age_days'})
                        
                        csv_data = chunk.drop(columns=cols_to_drop, errors='ignore').to_csv(index=False, sep=detected_sep)
                        zip_file.writestr(f"{chunk_name}.csv", csv_data)
                        
                        project_rows.append({
                            "File": chunk_name,
                            "Project Type": "AI Agent",
                            "Contacts Added": len(chunk),
                            "Status": "Ready"
                        })
                
                progress_bar.progress((idx + 1) / len(buckets))
        
        status_text.empty()
        st.code("\n".join(stats_text), language="text")

        if project_rows:
            st.subheader("Project Files")
            st.dataframe(pd.DataFrame(project_rows), use_container_width=True, hide_index=True)

        st.download_button(
            label="Download split file (.zip)",
            data=zip_buffer.getvalue(),
            file_name=f"{project_prefix if project_prefix else 'Split'}_{today.strftime('%Y%m%d')}.zip",
            mime="application/zip"
        )
        
    except Exception as e:
        st.error(f"An error occurred while processing the file: {e}")
