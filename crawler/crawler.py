import hashlib
import tabula
import requests
import re
import os
import logging
from ftplib import FTP_TLS
from urlextract import URLExtract
from urllib.parse import urlparse
from datetime import datetime, timedelta
from io import BytesIO
from bs4 import BeautifulSoup
from .tools import build_logger


class UrlFetcher:
    def __init__(self):
        self.logger = build_logger("url_builder", "/opt/crawler/logs/")
        self.config = {"cz": {"url": os.environ["CZ_SOURCE"], "last_success": 1},
                       "sk": {"url": os.environ["SK_SOURCE"]},
                       "bg": {"url": os.environ["BG_SOURCE"]}}

    def test_url(self, url: str) -> bool:
        try:
            self.logger.info("Trying url {}".format(url))
            req = requests.head(url)
        except requests.exceptions.RequestException as e:
            self.logger.info("Failed to test url: {}, {}".format(url, e))
        else:
            return req.ok

    def get_cz(self) -> str:
        for i in range(self.config["cz"]["last_success"], self.config["cz"]["last_success"] + 50):
            url = self.config["cz"]["url"].format(i)
            if self.test_url(url):
                self.logger.info("MFCZ blacklist found on new url: {}".format(url))
                self.config["cz"]["last_success"] = i
                return url
        self.logger.warning("MFCZ blacklist was not found")

    def get_sk(self) -> str:
        last_monday = (datetime.now() - timedelta(days=datetime.now().weekday())).strftime("%d.%m.%Y")
        url = self.config["sk"]["url"].format(last_monday)
        if self.test_url(url):
            self.logger.info("MFSK blacklist found on url: {}".format(url))
            return url
        else:
            self.logger.warning("Failed to detect MFSK blacklist on url {}".format(url))

    def get_bg(self) -> str:
        try:
            req = requests.get(os.environ["BG_REFERENCE"])
        except requests.exceptions.RequestException as e:
            self.logger.warning("Failed to get bg base page, {}".format(e))
        else:
            if req.ok:
                soup = BeautifulSoup(req.content, 'html.parser')
                link = soup.find("ul", {"class": "docs"}).find("li").find("a")["href"]
                url = self.config["bg"]["url"].format(link)
                if self.test_url(url):
                    self.logger.info("MFBG blacklist found on url: {}".format(url))
                    return url
            else:
                self.logger.warning("Failed to get data from base MFBG website error {}".format(req.status_code))


class BlockListCrawler:
    def __init__(self):
        self.hash_cache = {source: "" for source in ["cz", "sk", "bg"]}
        self.logger = build_logger("crawler", "/opt/crawler/logs/")
        self.regex = re.compile(r'^[a-zA-Z\d-]{,63}(\.[a-zA-Z\d-]{,63})*$')
        self.extractor = URLExtract()
        self.url_fetcher = UrlFetcher()
        tracer = logging.getLogger('tabula')
        tracer.setLevel(logging.CRITICAL)

    def send_error(self, data: dict):
        try:
            requests.post(os.environ["ERROR_API"], json=data)
        except requests.exceptions.RequestException as re:
            self.logger.info("Failed to contact error api, {}".format(re))

    def get_pdf_hash(self, pdf):
        return hashlib.sha256(pdf).hexdigest()

    def get_pdf(self, url: str):
        try:
            req = requests.get(url)
        except requests.exceptions.RequestException as re:
            self.logger.warning("Failed to fetch pdf from {}, {}".format(url, re))
        else:
            if req.ok:
                return req.content

    def persist_to_sftp(self, source: str):
        name_translation = {"cz": "cr", "sk": "sk", "bg": "bg"}
        with FTP_TLS(os.environ["FTP_HOST"], user=os.environ["FTP_USERNAME"], passwd=os.environ["FTP_PASSWORD"]) as ftp:
            ftp.cwd(os.environ["FTP_PATH"])
            ftp.storbinary("STOR mf{}.csv".format(name_translation[source]),
                           open("/opt/crawler/exports/mf{}.csv".format(source), "rb"))
            self.logger.info("File uploaded for source {}".format(source))

    def write_csv(self, data: list, source: str):
        self.logger.info("Found {} domains from source mf{}".format(len(data), source))
        with open("/opt/crawler/exports/mf{}.csv".format(source), "w") as file:
            for domain in data:
                file.write("{}\n".format(domain))

    def url_to_fqdn(self, url: str) -> str:
        if "//" not in url:
            url = "//{}".format(url)
        return urlparse(url).hostname
        # self.url_logger.info(url)
        # if url.endswith("/"):
        #     url = url[:-1]
        # return url.split("//")[-1]

    def dump_content(self, pdf, source: str):
        index_map = {"cz": 0, "sk": 1, "bg": 1}
        try:
            tables = tabula.read_pdf(BytesIO(pdf), spreadsheet=True, pages='all', multiple_tables=True)
        except Exception as e:
            self.logger.warning("Failed to parse pdf {}, {}".format(source, e))
            self.send_error({"blocklist_crawler": "Failed to parse pdf {}, {}".format(source, e)})
        else:
            domain_data = []
            for table in tables:
                try:
                    index = index_map[source] + 1 if table[0].isnull().values.all() else index_map[source]
                    for column in table[index]:
                        if isinstance(column, str):
                            domains = [self.url_to_fqdn(url) for url in self.extractor.find_urls(column.lower())]
                            domain_data.extend(domains)
                except Exception as te:
                    self.logger.warning("Failed to process table for {}, {}".format(source, te), exc_info=True)
                    self.send_error({"blocklist_crawler": "Failed to process table for {}, {}".format(source, te)})
            if domain_data:
                self.write_csv(domain_data, source)
                self.logger.info("Blocklist downloaded and persisted from source mf{}".format(source))

    def get_all(self):
        for source, url in {"cz": self.url_fetcher.get_cz(),
                            "sk": self.url_fetcher.get_sk(),
                            "bg": self.url_fetcher.get_bg()}.items():
            try:
                if url:
                    pdf = self.get_pdf(url)
                    pdf_hash = self.get_pdf_hash(pdf)
                    if self.hash_cache[source] != pdf_hash:
                        self.hash_cache[source] = pdf_hash
                        self.dump_content(pdf, source)
                        self.persist_to_sftp(source)
                    else:
                        self.logger.info("Old version found for source {}, no change was made".format(source))
                else:
                    self.logger.info("No url found for source {}".format(source))
            except Exception as e:
                self.logger.warning("failed to process data for source {}, {}".format(source, e), exc_info=True)
                self.send_error({"blocklist_crawler": "Failed to get data from source mf{}, {}".format(source, e)})
