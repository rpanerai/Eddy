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
    def DecodeBatch(reply_string, base_id):
        raw_data = feedparser.parse(reply_string)
        data = [{
            "id": i + base_id,
            "type": "",
            "date": d["published"].split("T", 1)[0],
            "authors": [
                a["name"]
                for a in d.get('authors', [])
            ],
            "title": d.get("title", "").replace("\n ", ""),
            "abstract": d.get("summary", "").replace("\n", " "),
            "citations": "",
            "journal": d.get("arxiv_journal_ref", ""),
            "inspire_id": "",
            "texkey": "",
            "arxiv_id": d.get("id", "").rsplit("/abs/", 1)[1].rsplit("v", 1)[0],
            "dois": [d.get("arxiv_doi", "")]
        } for (i, d) in enumerate(raw_data["entries"])]

        total = int(raw_data["feed"]["opensearch_totalresults"])

        return (data, total)
