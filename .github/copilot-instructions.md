# TroubleSight Data-to-UI Explorer

TroubleSight is a Streamlit-based Python web application that transforms JSON data into interactive dashboards and visualizations through a configuration-driven ETL system. Users upload ZIP files containing JSON data, define extraction rules via YAML configurations, and instantly create queryable databases with beautiful UI components.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

### Bootstrap, Build, and Run
- **Create virtual environment**: `python3 -m venv venv` (takes ~5 seconds)
- **Activate virtual environment**:
  - Linux/macOS: `source venv/bin/activate`
  - Windows: `venv\Scripts\activate`
- **Install dependencies**: `pip install -r requirements.txt` (takes ~45 seconds. NEVER CANCEL. Set timeout to 60+ minutes)
  - If network timeouts occur, retry with: `pip install --timeout 300 -r requirements.txt`
  - Network issues may require firewall allowlisting for PyPI access
- **Run the application**: `python main.py` (starts in ~5-8 seconds)
  - Application will be available at `http://localhost:8080`
  - Uses custom ApplicationManager that handles Streamlit server lifecycle
  - Press Ctrl+C to stop all services gracefully

### Alternative Running Methods
- **Direct Streamlit**: `cd json2ui && streamlit run J2UI.py` (also runs on port 8080)
- **Virtual environment detection**: Application automatically detects and uses virtual environment if available

### Verified Timing Expectations
Based on testing with example data:
- **Virtual environment creation**: ~5 seconds
- **Dependency installation**: ~45 seconds (when network is stable)
- **Application startup**: ~5-8 seconds to full availability  
- **Example file processing**: ~2-3 seconds for 7 JSON files (3.8KB ZIP)
- **Chart rendering**: ~1-2 seconds per dashboard tab
- **File upload**: Nearly instantaneous for files under 10MB

### Dependencies and Requirements
- **Python version**: 3.8+ required (tested with 3.12.3)
- **Core dependencies**: `streamlit`, `pandas`, `pyyaml`, `jsonpath-ng`
- **Platform support**: Cross-platform (Windows, macOS, Linux)
- **No build step required**: Pure Python application with no compilation

## Validation and Testing

### Manual Validation Requirements
ALWAYS test actual functionality after making changes by running through complete user scenarios:

1. **Upload and Process Test Data**:
   - Use `json2ui/examples/example-json-files.zip` for testing
   - Upload via the web interface at `http://localhost:8080`
   - Click "🚀 Process JSON Files" 
   - Verify dashboard tabs appear (7 tabs total: Dashboard Overview, Server Infrastructure, Incident Management, Alerts Monitoring, Performance Metrics, Service Health, Cluster Status)
   - Expected processing time: ~2-3 seconds for example files

2. **Test Dashboard Functionality**:
   - Navigate between all dashboard tabs 
   - Verify charts, tables, and metrics display correctly
   - Check interactive elements (sorting, filtering, hover tooltips)
   - Check for any JavaScript console errors (some Vega-Lite warnings are normal)
   - Verify file upload and removal functionality works
   - **Expected results**: Server Status Overview table, CPU Usage Charts, performance metrics, alert counts

3. **Configuration Validation**:
   - Test with custom extraction YAML files in `json2ui/extraction/`
   - Test with custom tab configurations in `json2ui/tabs/`
   - Verify database creation and data extraction works correctly
   - **Expected behavior**: New tables created, data properly extracted via JSONPath expressions

### Screenshots for Validation
Example of working application: Shows data processing successfully with interactive dashboard tabs, charts displaying server metrics, and tabular data views.

### Common Validation Scenarios
- **Configuration changes**: Always test the full upload → process → display workflow
- **UI modifications**: Verify responsiveness and cross-browser compatibility  
- **ETL changes**: Test with various JSON file structures and sizes
- **Utility changes**: Verify file cleanup and background processes work correctly

## Code Structure and Navigation

### Key Projects and Directories
```
TroubleSight/
├── main.py                      # Application manager and entry point
├── requirements.txt             # Python dependencies (4 core packages)
├── json2ui/
│   ├── J2UI.py                 # Main Streamlit application
│   ├── .streamlit/config.toml  # Streamlit server configuration (port 8080)
│   ├── extraction/             # JSON extraction YAML configs (6 files)
│   │   ├── 01-servers.yaml     # Server inventory extraction rules
│   │   ├── 02-alerts.yaml      # Alert data extraction rules
│   │   └── ...                 # Additional extraction configs
│   ├── tabs/                   # Dashboard tab YAML configs (7 files)
│   │   ├── 1-Dashboard-Overview.yaml  # Main dashboard tab
│   │   ├── 2-Server-Infrastructure.yml # Server monitoring tab
│   │   └── ...                 # Additional dashboard tabs
│   ├── utils/
│   │   ├── ConfigDrivenETL.py  # Core ETL engine and database operations
│   │   └── FileCleaner.py      # Background file cleanup utility
│   ├── examples/               # Sample data for testing
│   │   ├── example-json-files/ # Individual JSON test files
│   │   └── example-json-files.zip # ZIP archive for upload testing
│   ├── pages/                  # Future Streamlit pages (currently empty)
│   └── static/                 # Static assets
└── tmp/                        # Temporary file storage (auto-created)
```

### Important Configuration Files
- **`.github/workflows/codeql.yml`**: GitHub Actions security scanning
- **`json2ui/.streamlit/config.toml`**: Streamlit server settings (port 8080, logging)
- **`.gitignore`**: Excludes virtual environment, cache files, temporary data
- **`requirements.txt`**: Minimal dependencies - only 4 packages needed

### Development Patterns
- **Configuration-driven design**: All data extraction and visualization defined in YAML
- **SQLite backend**: Automatic database creation in temporary directories  
- **Background processes**: File cleanup runs automatically every hour
- **Cross-platform compatibility**: Works on Windows, macOS, and Linux

## Common Development Tasks

### Adding New Data Sources
1. Create extraction YAML in `json2ui/extraction/` following existing pattern
2. Define table schema with JSONPath expressions for field extraction
3. Test with sample JSON files via upload interface
4. Verify database table creation and data population

### Creating New Dashboard Tabs
1. Create tab YAML in `json2ui/tabs/` with numeric prefix for ordering
2. Define SQL queries and display configurations (dataframe, chart, metric)
3. Reference tables created by extraction configurations
4. Test visualization rendering and data display

### Modifying Core ETL Logic
- **Primary file**: `json2ui/utils/ConfigDrivenETL.py`
- **Key methods**: `load_extraction_configs_from_dir()`, `process_zip_file()`
- **Database operations**: SQLite with automatic schema generation
- **Always test**: Full upload → extract → query → display workflow

### Configuration Reference Examples

**Extraction Configuration Pattern**:
```yaml
tables:
  table_name:
    file_pattern: "*.json"
    root_path: "$[*]"  # JSONPath to data root
    fields:
      - name: column_name
        path: "$.field_path"  # JSONPath to field
        type: TEXT|INTEGER|REAL
```

**Dashboard Tab Configuration Pattern**:
```yaml
description: "Tab description"
queries:
  Query Name:
    description: "Query description"
    sql: "SELECT * FROM table_name"
    display:
      type: dataframe|metric|line_chart|bar_chart
```

## Troubleshooting and Common Issues

### Application Startup Issues
- **Port 8080 in use**: Application will fail to start - stop other services or change port in config.toml
- **Missing virtual environment**: Application works with system Python but virtual environment recommended
- **Import errors**: Run `pip install -r requirements.txt` in activated virtual environment
- **Network connectivity**: pip install may fail due to firewall limitations - document as "pip install fails due to network restrictions" if this occurs

### File Processing Issues
- **ZIP file too large**: Default limit 200MB per file - check file size
- **Invalid JSON**: Check JSON syntax and structure before uploading
- **Extraction failures**: Verify JSONPath expressions in extraction YAML configs match your data structure
- **Database errors**: Check SQLite permissions in temporary directory

### Performance Considerations
- **Large datasets**: Processing time scales with file size and complexity
- **Memory usage**: Pandas operations load full datasets into memory
- **Browser timeouts**: For large files, increase browser timeout settings

### Development Environment Issues
- **Circuit breaker**: Application blocks execution if files exist in `./circuit-breaker/` directory
- **File cleanup**: Background process cleans `tmp/` files older than 1 hour automatically
- **Streamlit caching**: Use `@st.cache_resource` for expensive operations

## NO Testing Framework
- **Current state**: No unit tests, integration tests, or automated testing infrastructure exists
- **Validation approach**: Manual testing via web interface with example data required
- **Python syntax validation**: Use `python3 -m py_compile <file>` to check syntax of all Python files
  - Core files to validate: `main.py`, `json2ui/J2UI.py`, `json2ui/utils/ConfigDrivenETL.py`, `json2ui/utils/FileCleaner.py`
- **YAML validation**: Use `python3 -c "import yaml; yaml.safe_load(open('file.yml'))"` to validate YAML syntax (requires pyyaml)
- **JSON validation**: Use `python3 -c "import json; json.load(open('file.json'))"` to validate JSON syntax
- **Quick smoke test**: `python3 -c "import json2ui.J2UI; print('✅ Import successful')"` (requires dependencies)
- **Future consideration**: Could add pytest or similar framework if needed

## NO Linting or Code Formatting
- **Current state**: No linting tools (flake8, pylint) or formatters (black, autopep8) configured
- **Code style**: Follow existing patterns in codebase
- **Future consideration**: Could add pre-commit hooks or CI linting if desired

## Environment Variables and Secrets
- **No environment variables required**: Application runs with default settings
- **No secrets management**: All configuration via YAML files
- **Streamlit secrets**: Uses `.streamlit/secrets.toml` (gitignored) if needed for future features

## Debug and Logging
- **Application logs**: Displayed in console with timestamp and component name
- **Streamlit logs**: Custom format defined in config.toml
- **Browser console**: Check for JavaScript errors during chart rendering
- **File operations**: Detailed logging for ETL and file processing operations

Remember: Always validate your changes by uploading test data and verifying the complete user workflow functions correctly.