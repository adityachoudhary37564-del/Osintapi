from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import os
from pathlib import Path

app = Flask(__name__)
CORS(app)

# Global variables
ALL_DATA = {}
FILE_INFO = {}
TOTAL_RECORDS = 0

def load_all_excel_files():
    """Load all Excel files from excel_files folder"""
    global ALL_DATA, FILE_INFO, TOTAL_RECORDS
    
    excel_folder = '.'
    
    # Get all Excel files
    excel_files = list(Path(excel_folder).glob('*.xlsx'))
    
    if not excel_files:
        print("❌ No Excel files found!")
        return {}
    
    print(f"📂 Found {len(excel_files)} Excel file(s)")
    print("=" * 60)
    
    for file_path in excel_files:
        file_name = file_path.name
        print(f"\n📄 Loading: {file_name}")
        
        try:
            excel_data = pd.read_excel(file_path, sheet_name=None, dtype=str)
            
            FILE_INFO[file_name] = {
                'sheets': {},
                'total_records': 0
            }
            
            for sheet_name, df in excel_data.items():
                df.columns = df.columns.str.strip()
                
                unique_key = f"{file_name.replace('.xlsx', '')}||{sheet_name}"
                
                ALL_DATA[unique_key] = {
                    'file': file_name,
                    'sheet': sheet_name,
                    'data': df
                }
                
                FILE_INFO[file_name]['sheets'][sheet_name] = len(df)
                FILE_INFO[file_name]['total_records'] += len(df)
                TOTAL_RECORDS += len(df)
                
                print(f"   ✅ Sheet '{sheet_name}': {len(df)} records")
            
        except Exception as e:
            print(f"   ❌ Error loading {file_name}: {str(e)}")
    
    print("\n" + "=" * 60)
    print(f"📊 Total records: {TOTAL_RECORDS}")
    print(f"📁 Total files: {len(FILE_INFO)}")
    print(f"📑 Total sheets: {len(ALL_DATA)}")
    print("=" * 60)
    
    return ALL_DATA

def search_in_dataframe(df, search_term, columns=None):
    """Search in a dataframe"""
    if columns is None:
        columns = df.columns.tolist()
    
    results = []
    search_term = str(search_term).lower().strip()
    
    mask = pd.Series([False] * len(df))
    
    for col in columns:
        if col in df.columns:
            col_mask = df[col].astype(str).str.lower().str.contains(search_term, na=False)
            mask = mask | col_mask
    
    if mask.any():
        results = df[mask].to_dict('records')
    
    return results

def get_column_mapping():
    return {
        'mobile': ['Mobile', 'Mobile 2', 'Contact', 'Mobile No.', 'Mobile Number', 'Phone', 'Phone No.'],
        'name': ['Name', 'User Name', 'Full Name', 'Candidate Name'],
        'email': ['Email', 'Email ID', 'Email Address', 'E-mail'],
        'city': ['City', 'Location', 'Current City'],
        'education': ['Education', 'Qualification', 'Degree'],
        'designation': ['Designation', 'Job Title', 'Position'],
        'company': ['Company', 'Current Company', 'Organization'],
        'skills': ['Skills', 'Key Skills', 'Technical Skills'],
        'salary': ['Salary', 'Current Salary', 'Expected Salary'],
        'experience': ['Experience', 'Total Experience', 'Work Experience']
    }

@app.route('/api/search', methods=['GET'])
def search_all():
    search_term = request.args.get('q', '')
    
    if not search_term:
        return jsonify({
            'success': False,
            'message': 'Please provide search term (?q=your_search)',
            'data': None
        }), 400
    
    if not ALL_DATA:
        return jsonify({
            'success': False,
            'message': 'Database not loaded',
            'data': None
        }), 500
    
    all_results = {}
    total_found = 0
    
    for key, item in ALL_DATA.items():
        df = item['data']
        results = search_in_dataframe(df, search_term)
        
        if results:
            all_results[key] = {
                'file': item['file'],
                'sheet': item['sheet'],
                'count': len(results),
                'records': results[:5]
            }
            total_found += len(results)
    
    if total_found == 0:
        return jsonify({
            'success': False,
            'message': f'No records found for: {search_term}',
            'data': None
        }), 404
    
    return jsonify({
        'success': True,
        'message': f'Found {total_found} record(s) across {len(all_results)} sheet(s)',
        'total_results': total_found,
        'data': all_results
    }), 200

@app.route('/api/search/<field>', methods=['GET'])
def search_by_field(field):
    search_term = request.args.get('value', '')
    
    if not search_term:
        return jsonify({
            'success': False,
            'message': f'Please provide value (?value=your_search)',
            'data': None
        }), 400
    
    column_mapping = get_column_mapping()
    
    if field not in column_mapping:
        return jsonify({
            'success': False,
            'message': f'Invalid field. Available fields: {list(column_mapping.keys())}',
            'data': None
        }), 400
    
    possible_columns = column_mapping[field]
    all_results = {}
    total_found = 0
    
    for key, item in ALL_DATA.items():
        df = item['data']
        matching_cols = [col for col in df.columns if col in possible_columns]
        
        if matching_cols:
            results = search_in_dataframe(df, search_term, matching_cols)
            
            if results:
                all_results[key] = {
                    'file': item['file'],
                    'sheet': item['sheet'],
                    'count': len(results),
                    'records': results[:10]
                }
                total_found += len(results)
    
    if total_found == 0:
        return jsonify({
            'success': False,
            'message': f'No record found for {field}: {search_term}',
            'data': None
        }), 404
    
    return jsonify({
        'success': True,
        'message': f'Found {total_found} record(s)',
        'total_results': total_found,
        'data': all_results
    }), 200

@app.route('/api/database-info', methods=['GET'])
def get_database_info():
    return jsonify({
        'success': True,
        'message': 'Database information',
        'total_files': len(FILE_INFO),
        'total_sheets': len(ALL_DATA),
        'total_records': TOTAL_RECORDS,
        'files': FILE_INFO
    }), 200

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'success': True,
        'message': 'Job Database API is running!',
        'total_files': len(FILE_INFO),
        'total_sheets': len(ALL_DATA),
        'total_records': TOTAL_RECORDS,
        'available_endpoints': [
            '/api/search?q=keyword',
            '/api/search/mobile?value=9876543210',
            '/api/search/name?value=rahul',
            '/api/search/email?value=user@gmail.com',
            '/api/search/city?value=mumbai',
            '/api/search/designation?value=manager',
            '/api/search/company?value=tcs',
            '/api/search/skills?value=python',
            '/api/database-info'
        ]
    }), 200

if __name__ == '__main__':
    # Load Excel files on startup
    load_all_excel_files()
    # Run the app
    app.run(host='0.0.0.0', port=5000, debug=False)