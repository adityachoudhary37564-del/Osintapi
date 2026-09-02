from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
from pathlib import Path
import os

app = Flask(__name__)
CORS(app)

# =========================================================
# CONFIGURATION
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

ALL_DATA = []
FILE_INFO = []
TOTAL_RECORDS = 0


# =========================================================
# COLUMN MAPPING
# =========================================================

def get_column_mapping():
    return {
        "mobile": [
            "Mobile",
            "Mobile 2",
            "Contact",
            "Mobile No.",
            "Mobile Number",
            "Phone",
            "Phone No."
        ],
        "name": [
            "Name",
            "User Name",
            "Full Name",
            "Candidate Name"
        ],
        "email": [
            "Email",
            "Email ID",
            "Email Address",
            "E-mail"
        ],
        "city": [
            "City",
            "Location",
            "Current City"
        ],
        "education": [
            "Education",
            "Qualification",
            "Degree"
        ],
        "designation": [
            "Designation",
            "Job Title",
            "Position"
        ],
        "company": [
            "Company",
            "Current Company",
            "Organization"
        ],
        "skills": [
            "Skills",
            "Key Skills",
            "Technical Skills"
        ],
        "salary": [
            "Salary",
            "Current Salary",
            "Expected Salary"
        ],
        "experience": [
            "Experience",
            "Total Experience",
            "Work Experience"
        ]
    }


# =========================================================
# LOAD ALL EXCEL FILES
# =========================================================

def load_all_excel_files():
    global ALL_DATA, FILE_INFO, TOTAL_RECORDS

    ALL_DATA = []
    FILE_INFO = []
    TOTAL_RECORDS = 0

    # Find all Excel files in the same folder as app.py
    excel_files = list(BASE_DIR.glob("*.xlsx"))

    print("=" * 60)
    print("EXCEL DATABASE LOADING")
    print(f"App directory: {BASE_DIR}")
    print(f"Excel files found: {len(excel_files)}")

    if not excel_files:
        print("WARNING: No .xlsx files found!")
        print("Files in app directory:")

        try:
            for file in BASE_DIR.iterdir():
                print(" -", file.name)
        except Exception as e:
            print("Could not list files:", e)

        print("=" * 60)
        return

    column_mapping = get_column_mapping()

    for excel_file in excel_files:
        try:
            print(f"Loading: {excel_file.name}")

            sheets = pd.read_excel(
                excel_file,
                sheet_name=None,
                dtype=str,
                engine="openpyxl"
            )

            file_record_count = 0

            for sheet_name, df in sheets.items():

                if df is None or df.empty:
                    continue

                # Clean column names
                df.columns = [
                    str(col).strip()
                    for col in df.columns
                ]

                # Remove completely empty rows
                df = df.dropna(how="all")

                if df.empty:
                    continue

                # Convert all values to strings
                df = df.fillna("")

                for col in df.columns:
                    df[col] = df[col].astype(str).str.strip()

                # Add metadata
                df["_source_file"] = excel_file.name
                df["_source_sheet"] = str(sheet_name)

                ALL_DATA.append(df)

                records = len(df)
                file_record_count += records
                TOTAL_RECORDS += records

                print(
                    f"  Sheet: {sheet_name} | "
                    f"Records: {records} | "
                    f"Columns: {len(df.columns)}"
                )

            FILE_INFO.append({
                "file_name": excel_file.name,
                "sheets": len(sheets),
                "records": file_record_count
            })

            print(
                f"Loaded {excel_file.name}: "
                f"{file_record_count} records"
            )

        except Exception as e:
            print(
                f"ERROR loading {excel_file.name}: {str(e)}"
            )

            FILE_INFO.append({
                "file_name": excel_file.name,
                "sheets": 0,
                "records": 0,
                "error": str(e)
            })

    print("=" * 60)
    print(f"TOTAL FILES: {len(excel_files)}")
    print(f"TOTAL RECORDS: {TOTAL_RECORDS}")
    print(f"TOTAL DATAFRAMES: {len(ALL_DATA)}")
    print("=" * 60)


# =========================================================
# SEARCH FUNCTION
# =========================================================

def search_in_dataframe(df, search_term):
    search_term = str(search_term).strip().lower()

    if not search_term:
        return df.iloc[0:0]

    mask = pd.Series(False, index=df.index)

    for column in df.columns:
        if column.startswith("_"):
            continue

        try:
            column_mask = (
                df[column]
                .astype(str)
                .str.lower()
                .str.contains(
                    search_term,
                    case=False,
                    na=False,
                    regex=False
                )
            )

            mask = mask | column_mask

        except Exception:
            continue

    return df[mask]


# =========================================================
# CONVERT DATAFRAME TO JSON
# =========================================================

def dataframe_to_records(df):
    if df.empty:
        return []

    result = df.copy()

    # Convert NaN to empty string
    result = result.fillna("")

    # Convert everything to string
    for col in result.columns:
        result[col] = result[col].astype(str)

    return result.to_dict(orient="records")


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    return jsonify({
        "success": True,
        "message": "Job Database API is running!",
        "total_files": len(FILE_INFO),
        "total_records": TOTAL_RECORDS,
        "total_sheets": sum(
            item.get("sheets", 0)
            for item in FILE_INFO
        ),
        "available_fields": list(
            get_column_mapping().keys()
        ),
        "endpoints": {
            "database_info": "/api/database-info",
            "global_search": "/api/search?q=keyword",
            "field_search": "/api/search/<field>?value=value",
            "reload": "/api/reload"
        }
    })


# =========================================================
# DATABASE INFO
# =========================================================

@app.route("/api/database-info")
def database_info():
    return jsonify({
        "success": True,
        "message": "Job Database API is running!",
        "total_files": len(FILE_INFO),
        "total_records": TOTAL_RECORDS,
        "total_sheets": sum(
            item.get("sheets", 0)
            for item in FILE_INFO
        ),
        "files": FILE_INFO,
        "available_fields": list(
            get_column_mapping().keys()
        )
    })


# =========================================================
# GLOBAL SEARCH
# =========================================================

@app.route("/api/search")
def global_search():

    query = request.args.get("q", "").strip()

    if not query:
        return jsonify({
            "success": False,
            "message": "Please provide a search query using ?q="
        }), 400

    results = []

    for df in ALL_DATA:
        try:
            matched = search_in_dataframe(df, query)

            if not matched.empty:
                results.extend(
                    dataframe_to_records(matched)
                )

        except Exception as e:
            print("Search error:", e)

    return jsonify({
        "success": True,
        "query": query,
        "count": len(results),
        "results": results
    })


# =========================================================
# FIELD SEARCH
# =========================================================

@app.route("/api/search/<field>")
def field_search(field):

    value = request.args.get("value", "").strip()

    if not value:
        return jsonify({
            "success": False,
            "message": "Please provide ?value="
        }), 400

    mapping = get_column_mapping()

    field = field.lower().strip()

    if field not in mapping:
        return jsonify({
            "success": False,
            "message": f"Unknown field: {field}",
            "available_fields": list(mapping.keys())
        }), 400

    possible_columns = [
        col.lower()
        for col in mapping[field]
    ]

    results = []

    for df in ALL_DATA:

        # Create lowercase column lookup
        column_lookup = {
            str(col).strip().lower(): col
            for col in df.columns
        }

        for possible_column in possible_columns:

            if possible_column not in column_lookup:
                continue

            actual_column = column_lookup[possible_column]

            try:
                mask = (
                    df[actual_column]
                    .astype(str)
                    .str.lower()
                    .str.contains(
                        value.lower(),
                        case=False,
                        na=False,
                        regex=False
                    )
                )

                matched = df[mask]

                if not matched.empty:
                    results.extend(
                        dataframe_to_records(matched)
                    )

                break

            except Exception as e:
                print(
                    f"Field search error: {str(e)}"
                )

    return jsonify({
        "success": True,
        "field": field,
        "value": value,
        "count": len(results),
        "results": results
    })


# =========================================================
# RELOAD EXCEL DATABASE
# =========================================================

@app.route("/api/reload")
def reload_database():

    try:
        load_all_excel_files()

        return jsonify({
            "success": True,
            "message": "Excel database reloaded successfully!",
            "total_files": len(FILE_INFO),
            "total_records": TOTAL_RECORDS,
            "total_sheets": sum(
                item.get("sheets", 0)
                for item in FILE_INFO
            )
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": "Failed to reload database",
            "error": str(e)
        }), 500


# =========================================================
# STARTUP
# =========================================================

load_all_excel_files()


if __name__ == "__main__":

    port = int(
        os.environ.get("PORT", 5000)
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )