import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from utils.ConfigDrivenETL import ConfigDrivenETL
from utils.FileCleaner import FileCleaner

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any
from jsonpath_ng import parse
import shutil
import traceback
import uuid
import weakref
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format='[%(name)s] %(levelname)s %(asctime)s: %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger('J2UI')

st.markdown("""
    <style>
        .reportview-container {
            margin-top: -2em;
        }
        #MainMenu {visibility: hidden;}
        .stDeployButton {display:none;}
        footer {visibility: hidden;}
        #stDecoration {display:none;}
    </style>
""", unsafe_allow_html=True)

# File cleaner vars
CLEANUP_PATTERNS = [
    "../tmp/*"
]
CLEANUP_TIME = 1800
CLEANUP_INTERVAL = 600

def setup_directories_and_configs():
    """Create config directories and sample files if they don't exist."""
    Path("extraction").mkdir(exist_ok=True)
    Path("tabs").mkdir(exist_ok=True)

def display_results(df: pd.DataFrame, query_info: Dict[str, Any]):
    """Display query results based on config."""
    display_config = query_info.get('display', {})
    display_type = display_config.get('type', 'dataframe')

    if df.empty:
        st.info("Query returned no results.")
        return
    try:
        if display_type == 'metric':
            if df.shape == (1, 1):
                label = display_config.get('label', 'Result')
                value = df.iloc[0, 0]
                st.metric(label=label, value=value)
            else:
                st.warning("⚠️ **Metric Display Error**: Query must return a single row and column for 'metric' display.")
                st.dataframe(df, use_container_width=True)
        elif display_type == 'metrics':
            if df.shape[1] == 2:
                for item in df.values:
                    st.write(item[0] + ": " + item[1])
            else:
                st.warning("⚠️ **Metrics Display Error**: Query must return only two columns for 'metrics' display.")
                st.dataframe(df, use_container_width=True)
        elif display_type == 'one_row_rotate':
            if df.shape[0] == 1:
                transposed_df = pd.DataFrame({
                    'Column': df.columns,
                    'Value': df.iloc[0].values
                })
                st.dataframe(transposed_df, use_container_width=False, hide_index=True)
            else:
                st.warning("⚠️ **One-Row-Rotate Display Error**: Query must return a single row for 'one_row_rotate' display.")
                st.dataframe(df, use_container_width=True)
        
        elif display_type in ['line_chart', 'bar_chart', 'area_chart']:
            x_col = display_config.get('x')
            y_col = display_config.get('y')
            if not x_col or not y_col:
                st.warning(f"⚠️ **Chart Display Error**: Chart type '{display_type}' requires 'x' and 'y' to be defined in the display config.")
                st.dataframe(df, use_container_width=True)
            elif x_col not in df.columns or y_col not in df.columns:
                st.warning(f"⚠️ **Chart Display Error**: Columns '{x_col}' or '{y_col}' not found in the query result.")
                st.dataframe(df, use_container_width=True)
            else:
                chart_df = df.set_index(x_col)
                if display_type == 'line_chart':
                    st.line_chart(chart_df[y_col])
                elif display_type == 'bar_chart':
                    st.bar_chart(chart_df[y_col])
                elif display_type == 'area_chart':
                    st.area_chart(chart_df[y_col])
        elif display_type == 'magic':
            if not df.empty:
                df
        elif display_type == 'html_dataframe':
            # Display as a static HTML table
            st.markdown(df.to_html(escape=False,index=False,justify="left"), unsafe_allow_html=True)
        else: # Default to dataframe
            link_col = None
            for col in df.columns:
                if col.lower() == 'link' or " link" in col.lower() or "_link" in col.lower():
                    link_col = col
                    break
            if link_col:
                st.dataframe(
                    df,
                    use_container_width=False,
                    hide_index=True,
                    column_config={
                        link_col: st.column_config.LinkColumn(
                            label=link_col,
                            help="Click to open link",
                            display_text=link_col
                        )
                    }
                )
            else:
                st.dataframe(df, use_container_width=False,hide_index=True)

    except Exception as e:
        st.error(f"Failed to render display type '{display_type}'. Error: {e}")
        st.dataframe(df, use_container_width=True, hide_index=True)

@st.cache_resource #Should only run once, no touch!
def cleaner():
    file_cleaner_instance = FileCleaner(
        patterns=CLEANUP_PATTERNS,
        max_age_seconds=CLEANUP_TIME,
        interval_seconds=CLEANUP_INTERVAL
    )
    return file_cleaner_instance

def check_circuit_breaker(): # TODO: Move to a Utility class to share with all pages
    """
    Checks for a file in ./circuit-breaker and generate a popup to block functionality, if one exists
    If the file has text, include the text in the popup. Otherwise general "Down For Maintenance"
    """
    dir_path = "./circuit-breaker"
    if not os.path.exists(dir_path):
        return

    files = [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]
    if files:
        file_path = os.path.join(dir_path, files[0])
        with open(file_path, "r") as f:
            content = f.read().strip()
        if content:
            st.warning(content)
        else:
            st.warning("Down for Maintenance")
        st.stop()

def main():
    check_circuit_breaker() #If file in ./circuit-breaker then prevent further execution..in case of server issues/etc
    st.set_page_config(page_title="JSON-to-UI Explorer", layout="wide", page_icon="🗺️")
    st.title("🔎 JSON-to-UI Explorer")
    st.markdown("Extract and Analyze JSON data.")
    st.sidebar.success("Select a tool above.")

    setup_directories_and_configs()

    #Start the cleaner, unused is fine, DO NOT DELETE
    file_cleaner = cleaner()

    shouldExpand = 'etl' not in st.session_state
    with st.expander("🗂️ Upload ZIP File", expanded=shouldExpand):
        
        zip_file = st.file_uploader("Upload Compressed JSON Files", type=['zip'], key="zip_upload")

        if st.button("🚀 Process JSON Files", disabled=not zip_file):
            if "temp_dir" in st.session_state:
                try:
                    shutil.rmtree(st.session_state.temp_dir)
                except FileNotFoundError:
                    pass
                for key in list(st.session_state.keys()):
                    if key in ['temp_dir', 'db_path', 'etl', 'zip_file_path', 'extracted_files_path']:
                        del st.session_state[key]
            
            run_id = str(uuid.uuid4())
            temp_dir = Path(f"../tmp/{run_id}")
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            st.session_state.temp_dir = temp_dir
            st.session_state.zip_file_path = temp_dir / zip_file.name
            st.session_state.extracted_files_path = temp_dir / "extracted"
            st.session_state.db_path = temp_dir / f"{run_id}.db"

            with open(st.session_state.zip_file_path, "wb") as f:
                f.write(zip_file.getbuffer())

            etl = ConfigDrivenETL(db_path=str(st.session_state.db_path))
            st.session_state.etl = etl

            with st.spinner("Loading configurations and preparing database..."):
                etl.load_extraction_configs_from_dir("extraction")
                etl.load_tab_configs_from_dir("tabs")
                etl.create_tables_from_config()

            if not etl.extraction_config.get('tables'):
                 st.error("Extraction failed: No table configurations found in the 'extraction' directory.")
            else:
                with st.spinner(f"Extracting data from {zip_file.name}..."):
                    etl.extract_from_zip(zip_file, st.session_state.extracted_files_path, run_id)
                st.success("✅ Data extraction complete!")
                st.rerun()

    if 'etl' in st.session_state:
        st.markdown("---")
        unsorted_query_files = st.session_state.etl.query_config_by_file
        if not unsorted_query_files:
            st.info("No query configurations found in the 'tabs' directory. Add YAML files to see query tabs here.")
        else:
            to_remove=[]
            for file, data in unsorted_query_files.items():
                if st.session_state.etl.platform not in data.get('platform',''):
                    to_remove.append(file)
            for item in to_remove:
                del unsorted_query_files[item]
            sorted_query_items = sorted(unsorted_query_files.items())
            query_files = dict(sorted_query_items)

            tab_titles = [
                f"📁 {filename.split('-', 1)[1].rsplit('.', 1)[0].replace('-', ' ')}"
                for filename in query_files.keys()
                ]
            if len(tab_titles) > 0:
                tabs = st.tabs(tab_titles)
            
            for i, filename in enumerate(query_files.keys()):
                with tabs[i]:
                    query_config_file = query_files[filename]
                    tab_description = query_config_file.get('description',"")
                    if tab_description != "":
                        st.markdown(
                            f"""
                            <div style="background-color:#0A3322; padding:15px; border-radius:10px; margin-bottom:10px;">
                                <span style="font-size:1em; color:#f2f2f2;">{tab_description}</span>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                        st.markdown("---")
                    queries_in_file = query_config_file.get('queries', {})
                    
                    if not queries_in_file:
                        st.write("No queries defined in this file.")
                        continue

                    for query_name, query_info in queries_in_file.items():
                        result_description = query_info.get('description','')
                        st.subheader(f"`{query_name}`",help=result_description)
                        try:
                            with st.spinner(f"Running query: {query_name}..."):
                                df = st.session_state.etl.execute_query(query_name)
                            display_results(df, query_info)
                        except Exception as e:
                            st.error(f"Error executing query '{query_name}': {e}")
                            with st.expander("Error Details"):
                                st.code(traceback.format_exc())
                        
                        st.markdown("---")

        with st.expander("💻  Developer Tools"):
            db_file = st.session_state.db_path.resolve()
            st.code(f"Session ID: {st.session_state.etl.run_id}", language=None)

            st.subheader("Query Uploaded Data")
            custom_query = st.text_area(
                "Enter a test SQLite query:",
                value="SELECT * FROM general_info;"
            )
            display_option = st.selectbox(
                "Choose a display type (charts/etc not yet available to test here)",
                ("dataframe", "metric","metrics","one_row_rotate","html_dataframe","magic"),
            )
            if st.button("Execute Query"):
                try:
                    with st.spinner(f"Running test query..."):
                        df = st.session_state.etl.execute_direct_query(custom_query)
                    #TODO: Use on_change callback to display add'l options for chart-like display types
                    display_config = {'display':{'type':display_option}}
                    display_results(df, display_config)

                except Exception as e:
                    st.error(f"Error executing test query: {e}")
                    with st.expander("Error Details"):
                        st.code(traceback.format_exc())


                    
            st.markdown("---")
            with open(db_file, "rb") as file:
                btn = st.download_button(
                        label="Download SQLite DB File",
                        data=file,
                        file_name='j2ui_sqlite.db',
                        mime="application/octet-stream"
                    )

            if st.button("Show Tables & Schema"):
                cursor = st.session_state.etl.conn.cursor()
                tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
                
                if not tables:
                    st.write("No tables found in the database yet.")
                else:
                    for table in tables:
                        result = cursor.execute(f"SELECT source_file FROM {table[0]} LIMIT 1").fetchone()
                        if result is not None:
                            source_file = result[0]
                        else:
                            source_file = "No source file detected"
                        table_name = table[0]
                        st.subheader(f"Table: `{table_name}`")
                        st.write(f"**Source File: `{source_file}`**")
                        
                        result = cursor.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
                        if result is not None:
                            count = result[0]
                        else:
                            source_file = "No source file detected"
                        st.write(f"**Row count:** {count}")

                        columns = cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
                        col_df = pd.DataFrame(columns, columns=['cid', 'name', 'type', 'notnull', 'default', 'pk'])
                        st.dataframe(col_df[['name', 'type']], use_container_width=True)
    else:
        st.info("👋 Welcome! Please upload a ZIP file and click 'Process' to begin.")

    # Footer
    st.markdown("---")
    st.markdown("Built by the [ThatMattCat (GitHub)](https://github.com/ThatMattCat))")

if __name__ == "__main__":
    main()