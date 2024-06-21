from scraper_module import Bundesanzeiger
import os


if __name__ == "__main__":
    # path to company list
    script_dir = os.path.dirname(os.path.abspath(__file__))
    path_to_list = os.path.join(script_dir, 'data', 'companies.xlsx')

    # path_to_list = os.path.expanduser('~/data/glassdollar-companies-20.xslx')
    domain_column = 'domain'  # Replace with the actual column name or index of column
    company_column = 'name'  # Replace with the actual column name or index

    # call the function with the arguments
    Bundesanzeiger.fetch_reports(path_to_list, domain_column, company_column)
