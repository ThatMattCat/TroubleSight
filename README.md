# JSON-to-UI Explorer 🔎

A powerful, configuration-driven tool that transforms JSON data into interactive dashboards and visualizations. Upload your JSON files, define extraction rules, and instantly create queryable databases with beautiful UI components - all without writing code.

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.0%2B-red)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

## 📋 Overview

JSON-to-UI Explorer is a flexible ETL (Extract, Transform, Load) and visualization platform that:
- **Extracts** structured data from JSON files using configurable YAML rules
- **Transforms** the data into SQLite database tables
- **Loads** and displays the data through customizable dashboards
- **Visualizes** results using various display formats (charts, metrics, tables)

Perfect for analyzing API responses, log files, configuration dumps, or any JSON-structured data.

## ✨ Features

### Core Capabilities
- 📦 **Batch Processing**: Upload multiple JSON files via ZIP archives
- 🔧 **Configuration-Driven**: Define extraction rules and queries using simple YAML files
- 🗄️ **SQLite Backend**: Automatic database creation and schema generation
- 📊 **Multiple Visualizations**: Tables, charts, metrics, and custom displays
- 🔍 **JSONPath Support**: Powerful path expressions for complex data extraction
- 🧹 **Auto-Cleanup**: Background process to manage temporary files
- 🖥️ **Cross-Platform**: Works on Windows, macOS, and Linux

### Display Types
- **DataFrames**: Interactive, sortable tables
- **Metrics**: Single value displays with labels
- **Charts**: Line, bar, and area charts
- **One-Row Rotate**: Transposed single-row displays
- **HTML Tables**: Static HTML-rendered tables
- **Custom Displays**: Extensible display system

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/ThatMattCat/TroubleSight.git
cd TroubleSight
```

2. **Create a virtual environment**
```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Run the application**
```bash
python main.py
```

The application will start and be available at `http://localhost:8501`

## 📖 Usage Guide

### Step 1: Prepare Your JSON Files

Place your JSON files in a ZIP archive. Example JSON structure:
```json
{
  "service": "api-gateway",
  "metrics": [
    {
      "timestamp": "2025-01-15T00:00:00Z",
      "requests_per_second": 1250,
      "avg_latency_ms": 45
    }
  ]
}
```

### Step 2: Define Extraction Rules

Create YAML files in the `json2ui/extraction/` directory:

```yaml
# extraction/api-metrics.yml
tables:
  api_metrics:
    file_pattern: "metrics.json"
    root_path: "$.metrics[*]"
    parentFields:
      - name: service_name
        path: "$.service"
        type: TEXT
    fields:
      - name: timestamp
        path: "$.timestamp"
        type: TEXT
      - name: requests_per_second
        path: "$.requests_per_second"
        type: INTEGER
```

### Step 3: Create Query Tabs

Define queries and visualizations in `json2ui/tabs/`:

```yaml
# tabs/1-Dashboard.yml
description: "API Performance Dashboard"
queries:
  📊 Traffic Overview:
    description: "Requests per second over time"
    sql: |
      SELECT timestamp, requests_per_second
      FROM api_metrics
      ORDER BY timestamp
    display:
      type: line_chart
      x: timestamp
      y: requests_per_second
```

### Step 4: Upload and Analyze

1. Start the application
2. Upload your ZIP file
3. Click "Process JSON Files"
4. Navigate through the generated tabs to view your data

## 🏗️ Project Structure

```
TroubleSight/
├── main.py                      # Application manager
├── requirements.txt             # Python dependencies
├── json2ui/
│   ├── J2UI.py                 # Main Streamlit application
│   ├── extraction/             # JSON extraction configurations
│   │   ├── 01-servers.yaml
│   │   ├── 02-alerts.yaml
│   │   └── ...
│   ├── tabs/                   # Query and visualization configs
│   │   ├── 1-Dashboard.yml
│   │   ├── 2-Server-Status.yml
│   │   └── ...
│   ├── utils/
│   │   ├── ConfigDrivenETL.py # ETL engine
│   │   └── FileCleaner.py     # Temporary file management
│   └── examples/               # Sample JSON files
│       └── example-json-files/
└── tmp/                        # Temporary file storage
```

## 🔧 Configuration Reference

### Extraction Configuration

```yaml
tables:
  table_name:
    file_pattern: "*.json"        # Glob pattern for matching files
    root_path: "$"                # JSONPath to data root
    parentFields:                 # Fields from parent context
      - name: field_name
        path: "$.path.to.field"
        type: TEXT
    fields:                       # Fields to extract
      - name: column_name
        path: "$.field_path"
        type: TEXT|INTEGER|REAL
        default: null             # Optional default value
```

### Query Configuration

```yaml
description: "Tab description"
queries:
  Query Name:
    description: "Query description"
    sql: |
      SELECT * FROM table_name
    display:
      type: dataframe|metric|line_chart|bar_chart
      x: column_name              # For charts
      y: column_name              # For charts
    post_processing:              # Optional transformations
      - type: rename_columns
        mapping:
          old_name: new_name
```

## 🎯 Use Cases

- **API Monitoring**: Analyze API performance metrics and response data
- **Log Analysis**: Extract and visualize structured log data
- **Configuration Management**: Compare and track configuration changes
- **Test Results**: Aggregate and report on test execution data
- **IoT Data**: Process sensor readings and device telemetry
- **Business Intelligence**: Transform JSON exports into dashboards

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Streamlit](https://streamlit.io/) for the web interface
- Uses [JSONPath-NG](https://github.com/h2non/jsonpath-ng) for path expressions
- Powered by [SQLite](https://www.sqlite.org/) for data storage

## 📧 Contact

Created by [ThatMattCat](https://github.com/ThatMattCat)

---

**Note**: This project includes sample data files in the `examples` directory to help you get started quickly. Run the examples to see the full capabilities of the system!