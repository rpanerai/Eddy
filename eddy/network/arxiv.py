import urllib.parse
import feedparser

from PySide2.QtCore import QUrl
from PySide2.QtNetwork import QNetworkRequest


class ArXivPlugin():
    @staticmethod
    def CreateRequest(search_string, batch_size, page):
        url = (
            "http://export.arxiv.org/api/query?"
            + "search_query=" + urllib.parse.quote(search_string)
            + "&start=" + str((page - 1) * batch_size)
            + "&max_results=" + str(batch_size)
            + "&sortBy=submittedDate&sortOrder=descending"
        )
        request = QNetworkRequest(QUrl(url))

        return request

    @staticmethod
    def DecodeBatch(reply_string):
        raw_data = feedparser.parse(reply_string)
        data = [ArXivPlugin._DecodeEntry(d) for d in raw_data["entries"]]

        total = int(raw_data["feed"]["opensearch_totalresults"])

        return (data, total)

    @staticmethod
    def _DecodeEntry(entry):
        item = {}

        item["date"] = entry["published"].split("T", 1)[0]

        item["authors"] = [a["name"] for a in entry['authors']]

        item["title"] = entry["title"].replace("\n ", "")

        item["abstract"] = entry["summary"].replace("\n", " ")

        if "arxiv_journal_ref" in entry:
            item["journal"] = entry["arxiv_journal_ref"]

        item["arxiv_id"] = entry["id"].rsplit("/abs/", 1)[1].rsplit("v", 1)[0]

        if "arxiv_doi" in entry:
            item["dois"] = [entry["arxiv_doi"]]

        return item
