import streamlit as st
import sqlite3
import json
import yaml
import zipfile
import tempfile
import os
import fnmatch
import pandas as pd
from datetime import datetime
from pathlib import Path
from jsonpath_ng import parse
import shutil
import logging
from typing import Dict, List, Any

HOSTNAME = "localhost:8080" #TODO: auto-detecct

logging.basicConfig(
    level=logging.INFO,
    format='[%(name)s] %(levelname)s %(asctime)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('Backend')

class ConfigDrivenETL:

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.extraction_config = {'tables': {}}
        self.query_config = {'queries': {}}
        self.query_config_by_file = {}
        self.json_file_list = []
        self.run_id = None

    def load_extraction_configs_from_dir(self, dir_path: str):
        """Load and merge YAML configs for JSON extraction from a directory."""
        if not os.path.isdir(dir_path):
            return
        
        for filename in os.listdir(dir_path): #TODO: Allow sub-folders
            if filename.endswith(('.yaml', '.yml')):
                file_path = os.path.join(dir_path, filename)
                with open(file_path, 'r') as f:
                    config_data = yaml.safe_load(f)
                    if config_data and 'tables' in config_data:
                        self.extraction_config['tables'].update(config_data['tables'])

    def load_tab_configs_from_dir(self, dir_path: str):
        """Load and merge YAML configs for database queries from a directory."""
        if not os.path.isdir(dir_path):
            return

        for filename in os.listdir(dir_path): #TODO: Allow subfolders
            if filename.endswith(('.yaml', '.yml')):
                file_path = os.path.join(dir_path, filename)
                with open(file_path, 'r') as f:
                    config_data = yaml.safe_load(f)
                    if config_data and 'queries' in config_data:
                        self.query_config_by_file[filename] = config_data
                        self.query_config['queries'].update(config_data['queries'])

    def create_tables_from_config(self):
        """
        Create SQLite tables based on the merged extraction config, including parent fields.
        """
        cursor = self.conn.cursor()
        for table_name, table_config in self.extraction_config.get('tables', {}).items():
            fields = table_config.get('fields', [])
            parent_fields = table_config.get('parentFields', [])
            all_fields = parent_fields + fields
            if all_fields != []:
                columns = [f"{field['name']} {field.get('type', 'TEXT')}" for field in all_fields]
                columns.append("source_file TEXT")
            else:
                columns = ["key TEXT","value TEXT","source_file TEXT"] #for auto-kv extraction
            create_stmt = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns)})"
            cursor.execute(create_stmt)
        self.conn.commit()

    def extract_from_zip(self, zip_file_obj, extract_to_path: Path, run_uuid: str = None):
        """Extracts zip to a specific path and processes the JSON files."""
        self.run_id = run_uuid
        extraction_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        extract_to_path.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_file_obj, 'r') as zf:
            zf.extractall(extract_to_path)
        # # Use to save specific filepaths to session state, for use in other streamlit pages
        # for root, _, files in os.walk(extract_to_path):
        #     for file in files:
        #         if file == 'some_file.abc':
        #             # This could now be accessed at st.session_state.etl.example_filepath in other pages
        #             self.example_filepath = os.path.join(root, file)
        for root, _, files in os.walk(extract_to_path):
            for file in files:
                if file.endswith('.json') and not file.startswith('_') and not file.startswith('.'):
                    file_path = os.path.join(root, file)
                    self.json_file_list.append(file_path)
                    self.process_json_file(file_path, file, extraction_id)

    def process_json_file(self, file_path: str, file_name: str, extraction_id: str):
        """Process a single JSON file based on the extraction config."""
        with open(file_path, 'r') as f:
            try:
                json_data = json.load(f)
            except json.JSONDecodeError:
                st.warning(f"Could not decode JSON from {file_name}. Skipping.")
                return
            except Exception as e:
                st.warning(f"Error parsing {file_name}: {e}. Skipping.")
                return

        cursor = self.conn.cursor()
        
        for table_name, table_config in self.extraction_config.get('tables', {}).items():
            if not fnmatch.fnmatch(file_name, table_config.get('file_pattern', '*')):
                continue
            
            # Pre-compile all JSONPath expressions
            root_expr = parse(table_config.get('root_path', '$'))
            parent_fields_config = table_config.get('parentFields', [])
            
            parent_field_exprs = []
            if parent_fields_config:
                for field in parent_fields_config:
                    parent_field_exprs.append({
                        'name': field['name'],
                        'expr': parse(field['path']),
                        'default': field.get('default')
                    })
            
            field_exprs = []
            for field in table_config.get('fields', []):
                field_exprs.append({
                    'name': field['name'],
                    'expr': parse(field['path']),
                    'default': field.get('default')
                })
            
            batch_rows = []
            batch_size = 1000  # TODO: Load test against memory usage
            
            root_matches = root_expr.find(json_data)
            total_matches = len(list(root_matches))
            # reset root matches due to total_matches logic - Keep this
            root_matches = root_expr.find(json_data)
            
            for idx, root_match in enumerate(root_matches):
                parent_row_data = {}
                
                # Parent field lookup - must be done per match due to potential nested wildcards
                if parent_field_exprs:
                    parent_data = None
                    ascendant_match = root_match.context # context = parent
                    # Allows 'parent' field to be any parent. First match going up, wins
                    while ascendant_match:
                        if parent_field_exprs[0]['expr'].find(ascendant_match.value):
                            parent_data = ascendant_match.value
                            break
                        ascendant_match = ascendant_match.context
                    
                    if parent_data:
                        for pfield in parent_field_exprs:
                            matches = pfield['expr'].find(parent_data)
                            value = matches[0].value if matches else pfield['default']
                            if isinstance(value, (list, dict)):
                                value = json.dumps(value)
                            parent_row_data[pfield['name']] = value # eg: parent_row_data['parentId'] = 1234
                
                items = [root_match.value] if not isinstance(root_match.value, list) else root_match.value
                
                for item in items:
                    # auto-kv extraction if no fields are defined
                    if field_exprs == [] and isinstance(item,dict):
                        for key,value in item.items():
                            row_data = parent_row_data.copy()
                            row_data['key'] = key
                            if isinstance(value, (dict, list)):
                                row_data['value'] = json.dumps(value)
                            else:
                                row_data['value'] = value
                            row_data['source_file'] = file_name #TODO: inefficient
                            batch_rows.append(row_data)
                            if len(batch_rows) >= batch_size:
                                self._insert_batch(cursor, table_name, batch_rows)
                                batch_rows = []

                    else:
                        row_data = parent_row_data.copy()
                        for fexpr in field_exprs:
                            matches = fexpr['expr'].find(item)
                            value = matches[0].value if matches else fexpr['default']
                            if isinstance(value, (list, dict)):
                                value = json.dumps(value)
                            row_data[fexpr['name']] = value
                        
                        row_data['source_file'] = file_name
                        batch_rows.append(row_data)
                    
                        if len(batch_rows) >= batch_size:
                            self._insert_batch(cursor, table_name, batch_rows)
                            batch_rows = []
            # cleanup remaining
            if batch_rows:
                self._insert_batch(cursor, table_name, batch_rows)
        
        self.conn.commit()

    def _insert_batch(self, cursor, table_name: str, rows: List[Dict]):
        """Insert a batch of rows efficiently."""
        if not rows:
            return
        columns = list(rows[0].keys())
        placeholders = ', '.join(['?' for _ in columns])
        insert_stmt = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        values_list = [tuple(row[col] for col in columns) for row in rows]
        cursor.executemany(insert_stmt, values_list)

    def execute_query(self, query_name: str) -> pd.DataFrame:
        """Execute a named query from the merged query config."""
        query_info = self.query_config.get('queries', {}).get(query_name)
        if not query_info:
            raise ValueError(f"Query '{query_name}' not found in config")
        
        df = pd.read_sql_query(query_info['sql'], self.conn, params=query_info.get('params', {}))
        
        for step in query_info.get('post_processing', []):
            if step['type'] == 'rename_columns':
                df = df.rename(columns=step['mapping'])
            elif step['type'] == 'filter':
                df = df.query(step['condition'])
        return df
    
    def execute_direct_query(self, query: str, query_info: dict = {}) -> pd.DataFrame:
        """Execute a query directly by providing the SQL and optional query info(modifications)."""

        df = pd.read_sql_query(query, self.conn, params=query_info.get('params', {}))
        
        for step in query_info.get('post_processing', []):
            if step['type'] == 'rename_columns':
                df = df.rename(columns=step['mapping'])
            elif step['type'] == 'filter':
                df = df.query(step['condition'])
        return df
    
    def close(self):
        """Close the database connection."""
        self.conn.close()

################ Custom File Editing Below ##################################
#
#  Careful, we are changing the file structures from their expected format
#  Generally okay to add data but not remove or modify existing data
#
#############################################################################

    def danger_modify(self):
        return