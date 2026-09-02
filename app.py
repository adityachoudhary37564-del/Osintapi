from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
from pathlib import Path
import re
import threading

app = Flask(__name__)
CORS(app)

# ============================================================
# GLOBAL DATABASE
# ============================================================

ALL_DATA = {}
FILE_INFO = {}
TOTAL_RECORDS = 0
DATA_LOCK = threading.Lock()


# ============================================================
# COLUMN MAPPING
# ============================================================

COLUMN_MAPPING = {
    "mobile": [
        "mobile",
        "mobile 2",
        "contact",
        "mobile no.",
        "mobile number",
        "phone",
        "phone no.",
        "phone number",
        "contact number",
        "contact no."
    ],
    "name": [
        "name",
        "user name",
        "full name",
        "candidate name"
    ],
    "email": [
        "email",
        "email id",
        "email address",
        "e-mail",
        "e-mail id"
    ],
    "city": [
        "city",
        "location",
        "current city"
    ],
    "education": [
        "education",
        "qualification",
        "degree"
    ],
    "designation": [
        "designation",
        "job title",
        "position"
    ],
    "company": [
        "company",
        "current company",
        "organization",
        "organisation"
    ],
    "skills": [
        "skills",
        "key skills",
        "technical skills"
    ],
    "salary": [
        "salary",
        "current salary",
        "expected salary"
    ],
    "experience": [
        "experience",
        "total experience",
        "work experience"
    ]
}


# ============================================================
# NORMALIZE COLUMN NAME
# ============================================================

def normalize_column_name(column):
    """Make column names easier to compare."""

    if column is None:
        return ""

    return " ".join(
        str(column)
        .strip()
        .lower()
        .split()
    )


# ============================================================
# LOAD ALL EXCEL FILES
# ============================================================

def load_all_excel_files():
    """Load all Excel files from the current folder."""

    global ALL_DATA
    global FILE_INFO
    global TOTAL_RECORDS

    with DATA_LOCK:

        # Clear old data
        ALL_DATA = {}
        FILE_INFO = {}
        TOTAL_RECORDS = 0

        excel_folder = Path(".")

        # Support both .xlsx and .xls
        excel_files = sorted(
            list(excel_folder.glob("*.xlsx")) +
            list(excel_folder.glob("*.xls"))
        )

        if not excel_files:
            print("❌ No Excel files found in current folder!")
            return False

        print("\n" + "=" * 70)
        print(f"📂 Found {len(excel_files)} Excel file(s)")
        print("=" * 70)

        for file_path in excel_files:

            file_name = file_path.name

            print(f"\n📄 Loading: {file_name}")

            try:

                # Read every sheet
                excel_data = pd.read_excel(
                    file_path,
                    sheet_name=None,
                    dtype=str
                )

                FILE_INFO[file_name] = {
                    "sheets": {},
                    "total_records": 0
                }

                for sheet_name, df in excel_data.items():

                    # Clean column names
                    df.columns = [
                        str(col).strip()
                        for col in df.columns
                    ]

                    # Replace NaN with empty string
                    df = df.fillna("")

                    unique_key = (
                        f"{file_path.stem}||{sheet_name}"
                    )

                    ALL_DATA[unique_key] = {
                        "file": file_name,
                        "sheet": str(sheet_name),
                        "data": df
                    }

                    record_count = len(df)

                    FILE_INFO[file_name]["sheets"][
                        str(sheet_name)
                    ] = record_count

                    FILE_INFO[file_name]["total_records"] += (
                        record_count
                    )

                    TOTAL_RECORDS += record_count

                    print(
                        f"   ✅ {sheet_name}: "
                        f"{record_count} records | "
                        f"{len(df.columns)} columns"
                    )

            except Exception as e:

                print(
                    f"   ❌ Error loading "
                    f"{file_name}: {str(e)}"
                )

                FILE_INFO[file_name] = {
                    "sheets": {},
                    "total_records": 0,
                    "error": str(e)
                }

        print("\n" + "=" * 70)
        print(f"📊 Total records : {TOTAL_RECORDS}")
        print(f"📁 Total files   : {len(FILE_INFO)}")
        print(f"📑 Total sheets  : {len(ALL_DATA)}")
        print("=" * 70)

    return True


# ============================================================
# SEARCH DATAFRAME
# ============================================================

def search_in_dataframe(df, search_term, columns=None):
    """Search text inside selected DataFrame columns."""

    if df.empty:
        return []

    if columns is None:
        columns = df.columns.tolist()

    search_term = str(search_term).strip()

    if not search_term:
        return []

    # Escape regex characters.
    # This prevents problems with values like:
    # +91, ., *, (, ), [, ], etc.
    search_pattern = re.escape(search_term)

    mask = pd.Series(
        False,
        index=df.index
    )

    for column in columns:

        if column not in df.columns:
            continue

        try:

            column_mask = (
                df[column]
                .astype(str)
                .str.contains(
                    search_pattern,
                    case=False,
                    na=False,
                    regex=True
                )
            )

            mask = mask | column_mask

        except Exception:
            continue

    if not mask.any():
        return []

    return df.loc[mask].to_dict("records")


# ============================================================
# GET MATCHING COLUMNS
# ============================================================

def get_matching_columns(df, field):
    """Find Excel columns matching requested field."""

    wanted_columns = COLUMN_MAPPING.get(field, [])

    normalized_wanted = {
        normalize_column_name(col)
        for col in wanted_columns
    }

    matching_columns = []

    for column in df.columns:

        normalized_column = normalize_column_name(column)

        if normalized_column in normalized_wanted:
            matching_columns.append(column)

    return matching_columns


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "success": True,
        "message": "Job Database API is running!",
        "total_files": len(FILE_INFO),
        "total_sheets": len(ALL_DATA),
        "total_records": TOTAL_RECORDS,
        "endpoints": {
            "global_search": "/api/search?q=keyword",
            "field_search": "/api/search/<field>?value=value",
            "database_info": "/api/database-info",
            "reload": "/api/reload"
        },
        "available_fields": list(COLUMN_MAPPING.keys())
    }), 200


# ============================================================
# GLOBAL SEARCH
# ============================================================

@app.route("/api/search", methods=["GET"])
def search_all():

    search_term = request.args.get("q", "").strip()

    if not search_term:

        return jsonify({
            "success": False,
            "message": "Please provide search term.",
            "example": "/api/search?q=rahul"
        }), 400

    if not ALL_DATA:

        return jsonify({
            "success": False,
            "message": "Database is empty or Excel files were not loaded."
        }), 500

    all_results = {}
    total_found = 0

    for key, item in ALL_DATA.items():

        df = item["data"]

        results = search_in_dataframe(
            df,
            search_term
        )

        if results:

            all_results[key] = {
                "file": item["file"],
                "sheet": item["sheet"],
                "count": len(results),

                # Return first 10 records
                "records": results[:10]
            }

            total_found += len(results)

    if total_found == 0:

        return jsonify({
            "success": False,
            "message": f"No records found for: {search_term}",
            "total_results": 0,
            "data": {}
        }), 404

    return jsonify({
        "success": True,
        "message": (
            f"Found {total_found} record(s) "
            f"across {len(all_results)} sheet(s)"
        ),
        "total_results": total_found,
        "data": all_results
    }), 200


# ============================================================
# FIELD SEARCH
# ============================================================

@app.route("/api/search/<field>", methods=["GET"])
def search_by_field(field):

    field = field.strip().lower()

    search_term = request.args.get(
        "value",
        ""
    ).strip()

    if not search_term:

        return jsonify({
            "success": False,
            "message": "Please provide value.",
            "example": (
                f"/api/search/{field}?value=example"
            )
        }), 400

    if field not in COLUMN_MAPPING:

        return jsonify({
            "success": False,
            "message": "Invalid field.",
            "available_fields": list(
                COLUMN_MAPPING.keys()
            )
        }), 400

    if not ALL_DATA:

        return jsonify({
            "success": False,
            "message": "Database is empty."
        }), 500

    all_results = {}
    total_found = 0

    for key, item in ALL_DATA.items():

        df = item["data"]

        matching_columns = get_matching_columns(
            df,
            field
        )

        if not matching_columns:
            continue

        results = search_in_dataframe(
            df,
            search_term,
            matching_columns
        )

        if results:

            all_results[key] = {
                "file": item["file"],
                "sheet": item["sheet"],
                "count": len(results),
                "records": results[:10]
            }

            total_found += len(results)

    if total_found == 0:

        return jsonify({
            "success": False,
            "message": (
                f"No record found for "
                f"{field}: {search_term}"
            ),
            "total_results": 0,
            "data": {}
        }), 404

    return jsonify({
        "success": True,
        "message": (
            f"Found {total_found} "
            f"{field} record(s)"
        ),
        "total_results": total_found,
        "data": all_results
    }), 200


# ============================================================
# DATABASE INFORMATION
# ============================================================

@app.route("/api/database-info", methods=["GET"])
def get_database_info():

    return jsonify({
        "success": True,
        "message": "Database information",
        "total_files": len(FILE_INFO),
        "total_sheets": len(ALL_DATA),
        "total_records": TOTAL_RECORDS,
        "files": FILE_INFO
    }), 200


# ============================================================
# RELOAD EXCEL FILES
# ============================================================

@app.route("/api/reload", methods=["GET"])
def reload_database():

    success = load_all_excel_files()

    if not success:

        return jsonify({
            "success": False,
            "message": "No Excel files found."
        }), 404

    return jsonify({
        "success": True,
        "message": "Excel database reloaded successfully.",
        "total_files": len(FILE_INFO),
        "total_sheets": len(ALL_DATA),
        "total_records": TOTAL_RECORDS
    }), 200


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(404)
def not_found(error):

    return jsonify({
        "success": False,
        "message": "API endpoint not found."
    }), 404


@app.errorhandler(500)
def internal_error(error):

    return jsonify({
        "success": False,
        "message": "Internal server error."
    }), 500


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    print("\n🚀 Starting Job Database API...")

    load_all_excel_files()

    print("\n🌐 Server starting on:")
    print("   http://127.0.0.1:5000")
    print("   http://0.0.0.0:5000")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )