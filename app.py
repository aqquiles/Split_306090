import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import math
import io
import zipfile

# --- UI Setup: Brightcall Aesthetic ---
st.set_page_config(page_title="RSC | Files", layout="wide")

# Custom CSS for dark mode compatibility and table visibility
st.markdown("""
    <style>
    /* Force table text to be visible in both light/dark themes */
    div[data-testid="stTable"] {
        background-color: transparent !important;
    }
    th { color: #4e73df !important; font-weight: bold !important; }
    
    /* Style the action button */
    .stButton>button {
        background-color: #4e73df;
        color: white;
        border-radius: 5px;
        border: none;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("Files")

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("Settings")
    date_col = st.text_input("Date Column", value="joindate")
    chunk_size = st.sidebar.number_input("Chunk Size", value=50000)
    delimiter = st.sidebar.selectbox("Delimiter", [",", ";"])

uploaded_file = st.file_uploader("Upload CSV to Split", type="csv")

if uploaded_file:
    # 1. Load Data
    df = pd.read_csv(uploaded_file, sep=delimiter)
    today = pd.Timestamp(2026, 2, 10) # Fixed date per your request
    
    # 2. Process Dates & Buckets
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

    # 3. Top Metrics Row (Summary Header)
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Rows", len(df))
    col2.metric("Date Reference", today.strftime('%Y-%m-%d'))
    col3.metric("Valid Dates", valid_mask.sum())

    # 4. Detailed Text Summary
    buckets = ["0-30_days", "30-60_days", "60-90_days", "outside_0_90", "invalid_date"]
    stats_text = [f"Today: {today.strftime('%Y-%m-%d')}", f"Total rows: {len(df)}"]
    
    project_rows = []
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for b in buckets:
            group = df[df['bucket'] == b]
            row_count = len(group)
            num_chunks = math.ceil(row_count / chunk_size) if row_count > 0 else 0
            
            # Add to text summary
            stats_text.append(f"{b.replace('_',' ')}: {row_count} rows, {num_chunks} chunk(s)")
            
            # Create Chunks and Table Rows
            if row_count > 0:
                for i in range(0, row_count, chunk_size):
                    chunk = group.iloc[i:i + chunk_size]
                    chunk_name = f"{b}_chunk{ (i//chunk_size)+1 :03d}"
                    
                    # Store CSV in ZIP
                    csv_data = chunk.drop(columns=['age_days', 'bucket'], errors='ignore').to_csv(index=False)
                    zip_file.writestr(f"{chunk_name}.csv", csv_data)
                    
                    # Add row to UI table
                    project_rows.append({
                        "File": chunk_name,
                        "Project Type": "AI Agent",
                        "Contacts Added": len(chunk),
                        "Status": "Ready"
                    })

    # Display Text Summary
    st.code("\n".join(stats_text), language="text")

    # 5. The "Projects" Table
    if project_rows:
        st.dataframe(pd.DataFrame(project_rows), use_container_width=True, hide_index=True)

    # 6. Action Button
    st.download_button(
        label="Download split file",
        data=zip_buffer.getvalue(),
        file_name=f"Split_{today.strftime('%Y%m%d')}.zip",
        mime="application/zip"
    )
