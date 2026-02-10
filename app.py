This is a great design choice. The **Brightcall.ai** interface is clean, professional, and uses a structured table layout that is much more functional for data processing than a simple list.

To match this, we will use Streamlit’s "Metric" components for the summary and a styled "Dataframe" for the chunk details. I’ve also updated the summary logic to match the exact text output you requested.

---

### Updated Code (`app.py`)

Replace your current code with this version to get the "Brightcall" look:

```python
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import math
import io
import zipfile

# --- UI Setup: Brightcall Style ---
st.set_page_config(page_title="Brightcall AI | CSV Splitter", layout="wide")

# Custom CSS to mimic the Brightcall sidebar/header feel
st.markdown("""
    <style>
    .main { background-color: #f8f9fc; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #e3e6f0; }
    div[data-testid="stExpander"] { border: none !important; box-shadow: none !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 Projects / CSV Splitter")

# --- Configuration ---
with st.sidebar:
    st.image("https://www.brightcall.ai/wp-content/uploads/2023/04/logo.svg", width=150) # Placeholder for logo
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
    today = pd.Timestamp.now().normalize()
    
    # Process Dates
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    valid_mask = df[date_col].notna()
    
    # Calculate Buckets
    df.loc[valid_mask, 'age_days'] = (today - df.loc[valid_mask, date_col]).dt.days
    df.loc[valid_mask, 'bucket'] = df.loc[valid_mask, 'age_days'].apply(get_bucket)
    df.loc[~valid_mask, 'bucket'] = "invalid_date"

    # --- Summary Section (Your requested format) ---
    st.subheader("Operation Summary")
    
    # Bucket stats calculation
    buckets = ["0-30_days", "30-60_days", "60-90_days", "outside_0_90", "invalid_date"]
    stats = {b: {"rows": 0, "chunks": 0} for b in buckets}
    
    for b in buckets:
        row_count = len(df[df['bucket'] == b])
        stats[b]["rows"] = row_count
        stats[b]["chunks"] = math.ceil(row_count / chunk_size) if row_count > 0 else 0

    # Displaying the text summary exactly as requested
    summary_box = f"""
    **Today:** {today.strftime('%Y-%m-%d')}  
    **Total rows:** {len(df)}  
    * **0-30 days:** {stats['0-30_days']['rows']} rows, {stats['0-30_days']['chunks']} chunk(s)  
    * **30-60 days:** {stats['30-60_days']['rows']} rows, {stats['30-60_days']['chunks']} chunk(s)  
    * **60-90 days:** {stats['60-90_days']['rows']} rows, {stats['60-90_days']['chunks']} chunk(s)  
    * **Outside 0-90:** {stats['outside_0_90']['rows']} rows, {stats['outside_0_90']['chunks']} chunk(s)  
    * **Invalid date:** {stats['invalid_date']['rows']} rows, {stats['invalid_date']['chunks']} chunk(s)
    """
    st.info(summary_box)

    # --- Project-Style Table (Mimicking the Screenshot) ---
    st.subheader("Project Chunks")
    
    project_rows = []
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for b in buckets:
            group = df[df['bucket'] == b]
            for i in range(0, len(group), chunk_size):
                chunk = group.iloc[i:i + chunk_size]
                chunk_name = f"{b}_chunk_{i//chunk_size + 1}"
                csv_data = chunk.drop(columns=['age_days', 'bucket'], errors='ignore').to_csv(index=False)
                zip_file.writestr(f"{chunk_name}.csv", csv_data)
                
                # Create row for the Brightcall-style table
                project_rows.append({
                    "Project": chunk_name,
                    "Type": "CSV Chunk",
                    "Rows Added": len(chunk),
                    "Bucket": b,
                    "Status": "Ready"
                })

    st.table(project_rows)

    st.download_button(
        label="➕ Add new project (Download All Chunks)",
        data=zip_buffer.getvalue(),
        file_name=f"Brightcall_Split_{today.strftime('%Y%m%d')}.zip",
        mime="application/zip",
        type="primary"
    )

```

---

### What changed?

1. **Sidebar Integration:** Added a sidebar for settings and a placeholder for the logo, similar to the left-hand navigation in the screenshot.
2. **The "Projects" Table:** Instead of just showing numbers, the app now generates a list of "Project Chunks" in a table format that looks like the **Projects** list in your image.
3. **Specific Summary:** I've coded the summary to output the exact rows-and-chunks count text you provided.
4. **The Blue Button:** The download button is now styled with `type="primary"` to mimic the blue **"+ Add new project"** button from your screenshot.

**Would you like me to add any specific colors or branding logos to make it look even more like the Brightcall portal?**
