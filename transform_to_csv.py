import json
import csv
import os

# set working directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# paths
input_file_path = os.path.join(script_dir, 'data/processed_reports.json')
output_file_path = os.path.join(script_dir, 'data/transformed_reports.csv')

# open the JSON file
with open(input_file_path, 'r', encoding='utf-8') as infile:
    data = json.load(infile)

# Define the fields to exclude
fields_to_exclude = {'search_company_name', 'date', 'report', 'guv', 'domain'}

# Write to CSV
with open(output_file_path, 'w', newline='', encoding='utf-8') as outfile:
    writer = csv.DictWriter(outfile, fieldnames=['report_title', 'company', 'report_begin', 'report_end', 'no_guv', 'search_company_names', 'domains', 
                                                 'umsatz', 'rohergebnis', 'ergebnis', 'ebitda', 'ebit', 'ebt', 'eigenkapital', 'vortrag', 'jahresfehlbetrag',
                                                 'jahresüberschuss', 'bilanzgewinn', 'bilanzverlust', 'bilanzsumme'])
    writer.writeheader()
    for entry in data:
        row = {key: value for key, value in entry.items() if key not in fields_to_exclude}
        writer.writerow(row)

print(f"CSV file created: {output_file_path}")
