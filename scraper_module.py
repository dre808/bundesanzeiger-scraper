import hashlib
import json
import os
from io import BytesIO
import pandas as pd

import dateparser
import numpy as np
import requests
from bs4 import BeautifulSoup

from typing import Dict

from pathlib import Path

from onnxruntime import InferenceSession
from PIL import Image


class Model:
    @staticmethod
    def load_image_arr(fp):
        image = Image.open(fp).convert("L")
        image = np.array(image)
        image = image / 255 * 2
        image = image - 1
        return image

    @staticmethod
    def character_indexes_to_str(character_indexes):
        ALPHABET = list("abcdefghijklmnopqrstuvwxyz0123456789")
        characters = np.array(ALPHABET)[character_indexes]
        return "".join(list(characters)).upper()

    @staticmethod
    def prediction_to_str(label):
        character_indexes = np.argmax(label, axis=1)
        return Model.character_indexes_to_str(character_indexes)

    @staticmethod
    def load_model():
        filepath = Path(__file__).parent / "assets" / "model.onnx"
        return InferenceSession(str(filepath))


class Config:
    proxy_config = None

    def __init__(self, proxies: Dict[str, str] = None):
        if proxies is not None and isinstance(proxies, dict):
            self.proxy_config = proxies

    def set_proxy(self, http_proxy: str, https_proxy: str):
        if self.proxy_config is None:
            self.proxy_config = {}
        self.proxy_config.update({"http": http_proxy, "https": https_proxy})

module_config = Config()


class Report:
    __slots__ = ["date", "name", "content_url", "company", "report", "guv"]

    def __init__(self, date, name, content_url, company, report=None, guv=None):
        self.date = date
        self.name = name
        self.content_url = content_url
        self.company = company
        self.report = report
        self.guv = guv

    def to_dict(self):
        return {
            "date": self.date,
            "name": self.name,
            "company": self.company,
            "report": self.report,
            "guv": self.guv
        }

    def to_hash(self):
        """MD5 hash of a the report."""

        dhash = hashlib.md5()

        entry = {
            "date": self.date.isoformat(),
            "name": self.name,
            "company": self.company,
            "report": self.report,
            "guv": self.guv
        }

        encoded = json.dumps(entry, sort_keys=True).encode("utf-8")
        dhash.update(encoded)

        return dhash.hexdigest()


class Bundesanzeiger:
    __slots__ = ["session", "model", "captcha_callback", "_config"]

    def __init__(self, on_captach_callback=None, config: Config = None):
        if config is None:
            self._config = module_config
        else:
            self._config = config

        self.session = requests.Session()
        if self._config.proxy_config is not None:
            self.session.proxies.update(self._config.proxy_config)
        if on_captach_callback:
            self.callback = on_captach_callback
        else:
            self.model = Model.load_model()
            self.captcha_callback = self.__solve_captcha

    def __solve_captcha(self, image_data: bytes):
        image = BytesIO(image_data)
        image_arr = Model.load_image_arr(image)
        image_arr = image_arr.reshape((1, 50, 250, 1)).astype(np.float32)

        prediction = self.model.run(None, {"captcha": image_arr})[0][0]
        prediction_str = Model.prediction_to_str(prediction)

        return prediction_str

    def __is_captcha_needed(self, entry_content: str):
        soup = BeautifulSoup(entry_content, "html.parser")
        return not bool(soup.find("div", {"class": "publication_container"}))

    def __find_all_entries_on_page(self, page_content: str):
        soup = BeautifulSoup(page_content, "html.parser")
        wrapper = soup.find("div", {"class": "result_container"})
        if wrapper is None:
            return []
        rows = wrapper.find_all("div", {"class": "row"})
        for row in rows:
            info_element = row.find("div", {"class": "info"})
            if not info_element:
                continue

            link_element = info_element.find("a")
            if not link_element:
                continue

            entry_link = link_element.get("href")
            entry_name = link_element.contents[0].strip()

            date_element = row.find("div", {"class": "date"})
            if not date_element:
                continue

            date = dateparser.parse(date_element.contents[0], languages=["de"])

            company_name_element = row.find("div", {"class": "first"})
            if not company_name_element:
                continue

            company_name = company_name_element.contents[0].strip()

            yield Report(date, entry_name, entry_link, company_name)

    def __find_guv(self, content_soup):
        guv_headline = None
        guv_table = None

        for element in content_soup.find_all():
            if element.name in ['h2', 'h3', 'h4'] and "gewinn" in element.text.lower() and "verlustrechnung" in element.text.lower():
                print("GuV gefunden")
                guv_headline = element
                guv_table = guv_headline.find_next("table")
                guv_content = [guv_headline, guv_table]
                guv_section = BeautifulSoup(''.join(str(element) for element in guv_content), "html.parser")
                return guv_section

        print("Keine GuV gefunden")
        return None

    def __generate_result(self, content: str):
        result = {}
        for element in self.__find_all_entries_on_page(content):
            get_element_response = self.session.get(element.content_url)

            if self.__is_captcha_needed(get_element_response.text):
                try:
                    soup = BeautifulSoup(get_element_response.text, "html.parser")
                    captcha_div = soup.find("div", {"class": "captcha_wrapper"})
                    if captcha_div is not None:
                        captcha_image_src = captcha_div.find("img")["src"]
                        img_response = self.session.get(captcha_image_src)
                        captcha_result = self.captcha_callback(img_response.content)
                        captcha_endpoint_url = soup.find_all("form")[1]["action"]
                        get_element_response = self.session.post(
                            captcha_endpoint_url,
                            data={"solution": captcha_result, "confirm-button": "OK"},
                        )
                    else:
                        print(f"Captcha not found, skipping element: {element.content_url}")
                        continue
                except Exception as e:
                    print(f"An error occurred while processing {element.content_url}: {e}")
                    continue

            content_soup = BeautifulSoup(get_element_response.text, "html.parser")
            content_element = content_soup.find("div", {"class": "publication_container"})

            if not content_element:
                continue

            element.report = content_element.text.strip() if content_element else ""

            guv_section = self.__find_guv(content_soup)
            if guv_section:
                element.guv = guv_section.text.strip()
            else:
                element.guv = ""

            result[element.to_hash()] = element.to_dict()
        return result

    def get_reports(self, company_name: str):
        company_name = company_name + " Jahresabschluss"

        self.session.cookies["cc"] = "1628606977-805e172265bfdbde-10"
        self.session.headers.update(
            {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7,et;q=0.6,pl;q=0.5",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "DNT": "1",
                "Host": "www.bundesanzeiger.de",
                "Pragma": "no-cache",
                "Referer": "https://www.bundesanzeiger.de/",
                "sec-ch-ua-mobile": "?0",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36",
            }
        )
        response = self.session.get("https://www.bundesanzeiger.de")
        response = self.session.get("https://www.bundesanzeiger.de/pub/de/start?0")
        response = self.session.get(
            f"https://www.bundesanzeiger.de/pub/de/start?0-2.-top%7Econtent%7Epanel-left%7Ecard-form=&fulltext={company_name}&area_select=22&search_button=Suchen"
        )
        return self.__generate_result(response.text)

    def fetch_reports(path_to_list, domain_column, company_column):
        companies_df = pd.read_excel(path_to_list)

        results_df = pd.DataFrame(columns=['search_company_name', 'domain', 'date', 'report_title', 'company', 'report', 'guv'])

        for _, row in companies_df.iterrows():
            search_company_name = row[company_column]
            domain = row[domain_column]

            try:
                ba = Bundesanzeiger()
                print(f"Searching for reports for {search_company_name}...")
                reports = ba.get_reports(search_company_name)
                print(f"Acquired {len(reports)} reports for {search_company_name}")

                if len(reports) > 0:
                    for report in reports.values():
                        report_data = {
                            'search_company_name': search_company_name,
                            'domain': domain,
                            'date': report['date'],
                            'report_title': report['name'],
                            'company': report['company'],
                            'report': report['report'],
                            'guv': report['guv']
                        }
                        results_df = pd.concat([results_df, pd.DataFrame([report_data])])
                    print("Successfully saved reports!")
            except Exception as e:
                print(f"An error occurred for {search_company_name}: {e}")
                continue

        results_df.to_json(os.path.join('data', 'reports.json'), orient='records', lines=False, force_ascii=False)
        print("Reports successfully exported to .json!")
