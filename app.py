from flask import Flask, request, jsonify
from flask_cors import CORS
from pathlib import Path
import pandas as pd
import os

app = Flask(__name__)
CORS(app)

# =========================================================
# PATH CONFIGURATION
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

ALL_DATA = []
FILE_INFO = []
TOTAL_RECORDS = 0


# =========================================================
# COLUMN MAPPING
# =========================================================

COLUMN_MAPPING = {
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
# FIND EXCEL FILES
# =========================================================

def find_excel_files():
    """
    Finds Excel files recursively from the folder
    where app.py is located.
    """

    files = []

    for pattern in ["*.xlsx", "*.xls"]:
        files.extend(BASE_DIR.rglob(pattern))

    # Remove duplicates
    unique_files = {}

    for file in files:
        unique_files[str(file.resolve())] = file

    return list(unique_files.values())


# =========================================================
# LOAD EXCEL DATABASE
# =========================================================

def load_all_excel_files():

    global ALL_DATA
    global FILE_INFO
    global TOTAL_RECORDS

    ALL_DATA = []
    FILE_INFO = []
    TOTAL_RECORDS = 0

    print("=" * 70)
    print("STARTING EXCEL DATABASE LOAD")
    print("BASE DIRECTORY:", BASE_DIR)
    print("=" * 70)

    excel_files = find_excel_files()

    print("EXCEL FILES FOUND:", len(excel_files))

    if not excel_files:

        print("WARNING: NO EXCEL FILES FOUND")

        try:
            print("FILES AVAILABLE IN BASE DIRECTORY:")

            for item in BASE_DIR.rglob("*"):
                if item.is_file():
                    print(" -", item.relative_to(BASE_DIR))

        except Exception as e:
            print("Directory scan error:", e)

        print("=" * 70)

        return

    for excel_file in excel_files:

        print()
        print("Loading:", excel_file.name)

        try:

            sheets = pd.read_excel(
                excel_file,
                sheet_name=None,
                dtype=str,
                engine="openpyxl"
            )

            file_records = 0
            valid_sheets = 0

            for sheet_name, df in sheets.items():

                if df is None or df.empty:
                    continue

                # Clean column names
                df.columns = [
                    str(column).strip()
                    for column in df.columns
                ]

                # Remove empty rows
                df = df.dropna(how="all")

                if df.empty:
                    continue

                # Replace NaN
                df = df.fillna("")

                # Convert values to string
                for column in df.columns:
                    df[column] = (
                        df[column]
                        .astype(str)
                        .str.strip()
                    )

                # Add source information
                df["_source_file"] = excel_file.name
                df["_source_sheet"] = str(sheet_name)

                ALL_DATA.append(df)

                records = len(df)

                file_records += records
                TOTAL_RECORDS += records
                valid_sheets += 1

                print(
                    "  Sheet:",
                    sheet_name,
                    "| Records:",
                    records,
                    "| Columns:",
                    len(df.columns)
                )

            FILE_INFO.append({
                "file_name": excel_file.name,
                "sheets": valid_sheets,
                "records": file_records,
                "path": str(
                    excel_file.relative_to(BASE_DIR)
                )
            })

            print(
                "SUCCESS:",
                excel_file.name,
                "| Records:",
                file_records
            )

        except Exception as e:

            print(
                "ERROR loading:",
                excel_file.name,
                "|",
                str(e)
            )

            FILE_INFO.append({
                "file_name": excel_file.name,
                "sheets": 0,
                "records": 0,
                "path": str(
                    excel_file.relative_to(BASE_DIR)
                ),
                "error": str(e)
            })

    print()
    print("=" * 70)
    print("DATABASE LOAD COMPLETE")
    print("TOTAL FILES:", len(FILE_INFO))
    print("TOTAL RECORDS:", TOTAL_RECORDS)
    print("TOTAL DATAFRAMES:", len(ALL_DATA))
    print("=" * 70)


# =========================================================
# DATAFRAME TO JSON
# =========================================================

def dataframe_to_records(df):

    if df is None or df.empty:
        return []

    result = df.copy()

    result = result.fillna("")

    for column in result.columns:
        result[column] = result[column].astype(str)

    return result.to_dict(orient="records")


# =========================================================
# GLOBAL SEARCH
# =========================================================

def search_dataframe(df, search_term):

    search_term = str(search_term).strip().lower()

    if not search_term:
        return df.iloc[0:0]

    mask = pd.Series(
        False,
        index=df.index
    )

    for column in df.columns:

        # Don't search internal columns
        if str(column).startswith("_"):
            continue

        try:

            current_mask = (
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

            mask = mask | current_mask

        except Exception:
            continue

    return df[mask]


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
            COLUMN_MAPPING.keys()
        ),
        "endpoints": {
            "database_info": "/api/database-info",
            "global_search": "/api/search?q=keyword",
            "field_search": "/api/search/<field>?value=value",
            "reload": "/api/reload",
            "debug_files": "/api/debug-files"
        }
    })


# =========================================================
# DATABASE INFO
# =========================================================

@app.route("/api/database-info")
def database_info():

    return jsonify({
        "success": True,
        "message": "Database information",
        "total_files": len(FILE_INFO),
        "total_records": TOTAL_RECORDS,
        "total_sheets": sum(
            item.get("sheets", 0)
            for item in FILE_INFO
        ),
        "files": FILE_INFO,
        "available_fields": list(
            COLUMN_MAPPING.keys()
        )
    })


# =========================================================
# DEBUG FILES
# =========================================================

@app.route("/api/debug-files")
def debug_files():

    try:

        all_files = []

        for file in BASE_DIR.rglob("*"):

            if file.is_file():

                all_files.append({
                    "name": file.name,
                    "path": str(
                        file.relative_to(BASE_DIR)
                    ),
                    "extension": file.suffix.lower(),
                    "size_bytes": file.stat().st_size
                })

        return jsonify({
            "success": True,
            "base_dir": str(BASE_DIR),
            "excel_files_detected": [
                {
                    "name": file.name,
                    "path": str(
                        file.relative_to(BASE_DIR)
                    ),
                    "size_bytes": file.stat().st_size
                }
                for file in find_excel_files()
            ],
            "total_files_found": len(all_files),
            "files": all_files
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =========================================================
# GLOBAL SEARCH
# =========================================================

@app.route("/api/search")
def global_search():

    query = request.args.get(
        "q",
        ""
    ).strip()

    if not query:

        return jsonify({
            "success": False,
            "message": "Please provide a search query using ?q="
        }), 400

    results = []

    for df in ALL_DATA:

        try:

            matched = search_dataframe(
                df,
                query
            )

            if not matched.empty:

                results.extend(
                    dataframe_to_records(matched)
                )

        except Exception as e:

            print(
                "Search error:",
                str(e)
            )

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

    value = request.args.get(
        "value",
        ""
    ).strip()

    if not value:

        return jsonify({
            "success": False,
            "message": "Please provide ?value="
        }), 400

    field = field.lower().strip()

    if field not in COLUMN_MAPPING:

        return jsonify({
            "success": False,
            "message": "Unknown field",
            "field": field,
            "available_fields": list(
                COLUMN_MAPPING.keys()
            )
        }), 400

    possible_columns = [
        column.lower()
        for column in COLUMN_MAPPING[field]
    ]

    results = []

    for df in ALL_DATA:

        column_lookup = {
            str(column).strip().lower(): column
            for column in df.columns
        }

        actual_column = None

        for possible_column in possible_columns:

            if possible_column in column_lookup:

                actual_column = column_lookup[
                    possible_column
                ]

                break

        if actual_column is None:
            continue

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

        except Exception as e:

            print(
                "Field search error:",
                str(e)
            )

    return jsonify({
        "success": True,
        "field": field,
        "value": value,
        "count": len(results),
        "results": results
    })


# =========================================================
# RELOAD DATABASE
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
            "message": "Database reload failed",
            "error": str(e)
        }), 500


# =========================================================
# LOAD DATABASE AT STARTUP
# =========================================================

load_all_excel_files()


# =========================================================
# RUN APP
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )