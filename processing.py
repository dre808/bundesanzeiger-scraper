import json
import re
import os
from datetime import datetime

# set working directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# paths
input_file_path = os.path.join(script_dir, 'data/reports.json')
output_file_path = os.path.join(script_dir, 'data/processed_reports.json')

# Define the regex patterns for various financial metrics
patterns = {
    "umsatz": r'umsatzerlöse[^\n]*\n[\s\n]*(-?\(?\d[ \d\.,]*\)?) *(?=\n)',
    "rohergebnis": r'rohergebnis[^\n]*\n[\s\n]*(-?\(?\d[ \d\.,]*\)?) *(?=\n)',
    "ergebnis": r'(ergebnis nach steuern|ergebnis des geschäftsjahres)[^\n]*\n[\s\n]*(-?\(?\d[ \d\.,]*\)?) *(?=\n)',
    "ebitda": r'(ebitda|ergebnis vor zinsen, steuern und abschreibungen|ergebnis vor zinsen, ertragsteuern, abschreibungen und amortisationen)[^\n]*\n[\s\n]*(-?\(?\d[ \d\.,]*\)?) *(?=\n)',
    "ebit": r'(ebit(?![a-zA-Z])|betriebsergebnis|ergebnis vor steuern, zinsen|ergebnis der gewöhnlichen geschäftstätigkeit|ergebnis vor zinsen und ertragssteuern|ergebnis vor zinsen und steuern)[^\n]*\n[\s\n]*(-?\(?\d[ \d\.,]*\)?) *(?=\n)',
    "ebt": r'(ergebnis vor steuern|ebt\)?) *\n[\s\n]*(-?\(?\d[ \d\.,]*\)?) *(?=\n)',
    "eigenkapital": r'eigenkapital[^\n]*\n[\s\n]*(-?\(?\d[ \d\.,]*\)?) *(?=\n)',    
    "vortrag": r'(verlustvortrag|gewinnvortrag)[^\n]*\n[\s\n]*(-?\(?\d[ \d\.,]*\)?) *(?=\n)',
    "jahresfehlbetrag": r'fehlbetrag[^\n]*\n[\s\n]*(-?\(?\d[ \d\.,]*\)?) *(?=\n)',
    "jahresüberschuss": r'überschuss[^\n]*\n[\s\n]*(-?\(?\d[ \d\.,]*\)?) *(?=\n)',     
    "bilanzgewinn": r'bilanzgewinn[^\n]*\n[\s\n]*(-?\(?\d[ \d\.,]*\)?) *(?=\n)',
    "bilanzverlust": r'bilanzverlust[^\n]*\n[\s\n]*(-?\(?\d[ \d\.,]*\)?) *(?=\n)',
    "bilanzsumme":r'(aktiva|passiva)[^\n]*\n[\s\n]*(-?\(?\d[ \d\.,]*\)?) *(?=\n)'
}

group_2_keys = {"ergebnis", "ebitda", "ebit", "ebt", "vortrag", "bilanzsumme"}


def mark_no_guv(entry):
    entry['no_guv'] = not bool(entry.get('guv', '').strip())
    return entry


def convert_timestamp_to_date(entry):
    date_pattern = r'\d{4}-\d{2}-\d{2}'
    if isinstance(entry['date'], str) and re.match(date_pattern, entry['date']):
        return entry
    
    timestamp_s = entry['date'] / 1000
    formatted_date = datetime.utcfromtimestamp(timestamp_s).strftime('%Y-%m-%d')
    entry['date'] = formatted_date
    return entry


def extract_start_and_end_date(entry, report_title):
    # check if report_begin is empty before attempting to extract it
    if not entry.get('report_begin'):
        begin_date_match = re.search(r'vom (\d{2}\.\d{2}\.\d{4})', report_title)
        if begin_date_match:
            entry['report_begin'] = begin_date_match.group(1)
    
    # check if report_end is empty before attempting to extract it
    if not entry.get('report_end'):
        end_date_match = re.search(r'zum (\d{2}\.\d{2}\.\d{4})', report_title)
        if end_date_match:
            entry['report_end'] = end_date_match.group(1)
    
    return entry


def extract_financials(entry):
    for key, pattern in patterns.items():
        match = re.search(pattern, entry.get("guv", ""), re.IGNORECASE)
        if not entry.get(key):
            if match:
                group_number = 2 if key in group_2_keys else 1
                value = match.group(group_number).replace('.', '').replace(',', '.').replace(' ', '')
                entry[key] = value
    return entry


def merge_duplicate_reports(data):
    unique_reports = {}
    
    for entry in data:
        report_key = (entry['report_title'], entry['company'])
        
        if report_key not in unique_reports:
            unique_reports[report_key] = entry
            unique_reports[report_key]['search_company_names'] = set([entry['search_company_name']])
            unique_reports[report_key]['domains'] = set([entry['domain']])
        else:
            unique_reports[report_key]['search_company_names'].add(entry['search_company_name'])
            unique_reports[report_key]['domains'].add(entry['domain'])
    
    # Convert sets to comma-separated strings
    for report in unique_reports.values():
        report['search_company_names'] = ', '.join(report['search_company_names'])
        report['domains'] = ', '.join(filter(None, report['domains']))
    
    return list(unique_reports.values())


def process_entry(entry):
    report_title = entry["report_title"]    
    entry = convert_timestamp_to_date(entry)
    entry = extract_start_and_end_date(entry, report_title)
    entry = extract_financials(entry)
    entry = mark_no_guv(entry)
    return entry


def sort_reports(data):

    # Sort the entries primarily by 'company' and secondarily by 'report_begin'
    data.sort(key=lambda x: x.get('report_begin', ''))  
    data.sort(key=lambda x: x.get('company', '').lower())
    return data

# Read the entire JSON file
with open(input_file_path, 'r', encoding='utf-8') as infile:
    data = json.load(infile)

# Process each entry in the JSON object
processed_data = [process_entry(entry) for entry in data]

# Get rid of duplicated reports but keeping every domain and search_company_name in 'domains' and 'search_company_names'
unique_data = merge_duplicate_reports(processed_data)


sorted_data = sort_reports(unique_data)

# Write the processed JSON back to a new file
with open(output_file_path, 'w', encoding='utf-8') as outfile:
    json.dump(unique_data, outfile, ensure_ascii=False, indent=4)