import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import io
import zipfile

# --- UI Setup ---
st.set_page_config(page_title="CSV Date Splitter", layout="wide")
st.title("📂 CSV Date-Based Splitter")
st.write("Upload a CSV to split it into age-based buckets (0-30, 30-60, 60-90 days).")

# --- Configuration Sidebar ---
st.sidebar.header("Settings")
date_col = st.sidebar.text_input("Date Column Name", value="joindate")
chunk_size = st.sidebar.number_input("Rows per Chunk", value=50000)
delimiter = st.sidebar.selectbox("Delimiter", [",", ";", "|"])

# --- Logic: Processing ---
def get_bucket(age):
    if 0 <= age < 30: return "0-30_days"
    if 30 <= age < 60: return "30-60_days"
    if 60 <= age <= 90: return "60-90_days"
    return "outside_0_90"

uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

if uploaded_file:
    # Read the CSV
    df = pd.read_csv(uploaded_file, sep=delimiter)
    
    if date_col not in df.columns:
        st.error(f"Column '{date_col}' not found! Check your settings.")
    else:
        # Convert to datetime (handles most formats automatically)
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        
        # Filter out invalid dates
        invalid_dates = df[df[date_col].isna()]
        valid_dates = df[df[date_col].notna()]
        
        # Calculate Age
        today = pd.Timestamp.now().normalize()
        valid_dates['age_days'] = (today - valid_dates[date_col]).dt.days
        valid_dates['bucket'] = valid_dates['age_days'].apply(get_bucket)
        
        # Prepare for Download
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            # Group by bucket and split into chunks
            for bucket_name, group in valid_dates.groupby('bucket'):
                for i in range(0, len(group), chunk_size):
                    chunk = group.iloc[i:i + chunk_size]
                    csv_data = chunk.drop(columns=['age_days', 'bucket']).to_csv(index=False)
                    zip_file.writestr(f"{bucket_name}_chunk_{i//chunk_size}.csv", csv_data)
            
            # Handle invalid dates
            if not invalid_dates.empty:
                zip_file.writestr("invalid_dates.csv", invalid_dates.to_csv(index=False))

        st.success("Processing Complete!")
        
        # --- Download Button ---
        st.download_button(
            label="📥 Download Split Files (.zip)",
            data=zip_buffer.getvalue(),
            file_name=f"split_files_{datetime.now().strftime('%Y%m%d')}.zip",
            mime="application/zip"
        )

        # --- Summary Table ---
        st.subheader("Summary Statistics")
        stats = valid_dates['bucket'].value_counts().reset_index()
        stats.columns = ['Bucket', 'Row Count']
        st.table(stats)
