# bundesanzeiger-scraper
Scrapes the Bundesanzeiger website. Bundesanzeiger is the official gazette and central platform for corporate disclosures and legal announcements in Germany. Able to retrieve annual balance sheets, income statements and extract important financial numbers from them.

The scraper module (scraper_module.py) interacts with the Bundesanzeiger website to retrieve financial reports for specified companies. The retrieved data is then processed and organized using the processing.py script. The scraper.py script serves as the entry point to initiate the scraping process.

## How to use

1. Install the required libraries by running 'pip install -r requirements.txt'

2. Place the companies.xlsx file containing the list of companies and domains in the data directory.

3. Open the scraper.py file and adjust the path_to_list, domain_column, and company_column variables as per your dataset and execute it. 

4. Once the scraping process completes, run the processing.py script.

5. Once the processing is completed, run the transform_to_csv.py script. 


## Expected output

The file processed_reports.json contains the results of scraping the Bundesanzeiger website. It includes the whole reports, which are scraped from Bundesanzeiger. Since the the reports are very long sometimes, data loss is possible when saving it in CSV. Therefore, only the relevant numbers are transformed into a CSV document afterwards. 

Description of the fields:

- search_company_name: the search term with which the the report was found on bundesanzeiger.de (these company names are taken from the companies.xslx list)
- date: date when report was published at Bundesanzeiger
- report_title: report title
- comapny: company name incl. legal form
- report: full report
- report_begin: start date of period for yearly report
- report_end: end date of period for yearly report
- umsatz: Umsatzerlöse from GuV
- rohergebnis: Rohergebnis from GuV
- ebidta: EBITDA from GuV
- ebit: EBIT from GuV
- ebt: EBT from GuV
- eigenkapital: Eigenkapital from balance sheet
- vortrag: Gewinn-/Verlustvortrag from balance sheet
- jahresfehlbetrag: Jahresfehlbetrag from balance sheet/GuV
- jahresüberschuss: Jahresüberschuss from balance sheet/GuV
- bilanzgewinn: Bilanzgewinn from balance sheet
- bilanzverlust: Bilanzverlust from balance sheet
- bilanzsumme: sum of balance sheet
- guv: chunk of the GuV
- domain: internet domain of the company used to search for the respective report
- no_guv: marks the reports, where no GuV could be identified


### Final CSV with financials

The file transformed_reports.csv contains all the financial numbers from the reports, sorted by company and begin_date of the report. 
