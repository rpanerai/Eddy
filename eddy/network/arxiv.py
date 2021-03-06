import urllib.parse
import feedparser

from PySide2.QtCore import QUrl
from PySide2.QtNetwork import QNetworkRequest


class ArXivPlugin():
    DEFAULT_BATCH_SIZE = 200

    @staticmethod
    def CreateRequest(search_string, batch_size, page):
        url = (
            "https://export.arxiv.org/api/query?"
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
        item["authors_bais"] = [None] * len(item["authors"])

        item["title"] = entry["title"].replace("\n ", "")

        item["abstract"] = entry["summary"].replace("\n", " ")

        if "arxiv_journal_ref" in entry:
            item["publication"] = entry["arxiv_journal_ref"]

        item["arxiv_id"] = entry["id"].rsplit("/abs/", 1)[1].rsplit("v", 1)[0]

        if "arxiv_doi" in entry:
            item["dois"] = [entry["arxiv_doi"]]

        return item


class ArXivNewPlugin(ArXivPlugin):
    @staticmethod
    def CreateFirstRequest(search_string):
        url = "https://export.arxiv.org/rss/" + search_string
        request = QNetworkRequest(QUrl(url))
        return request

    @classmethod
    def DecodeFirstRequest(cls, reply_string):
        raw_data = feedparser.parse(reply_string)
        news = [
            {"id": i["title"].split(":")[-1].split(" ")[0],
            "list": i["title"].split("[")[-1].split("]")[0],
            "new": i["title"][-8:-1] != "UPDATED"}
            for i in raw_data["entries"]
        ]
        if len(news) == 0:
            return ""

        list_ = raw_data["feed"]["title"].split(" ")[0]
        news = [d for d in news if cls.FilterItems(d, list_)]

        search_string = ",".join([i["id"] for i in news])
        # It could be useful to also pass the size of the batch,
        # size = len(news) + 1
        return search_string

    @staticmethod
    def FilterItems(item, list_):
        return True

    @staticmethod
    def CreateRequest(search_string, batch_size, page):
        url = (
            "https://export.arxiv.org/api/query?"
            + "id_list=" + urllib.parse.quote(search_string)
            + "&start=" + str((page - 1) * batch_size)
            + "&max_results=" + str(batch_size)
        )
        request = QNetworkRequest(QUrl(url))
        return request


class ArXivNewPlugin_News(ArXivNewPlugin):
    @staticmethod
    def FilterItems(item, list_):
        return item["list"] == list_ and item["new"]


class ArXivNewPlugin_CrossLists(ArXivNewPlugin):
    @staticmethod
    def FilterItems(item, list_):
        return item["list"] != list_ and item["new"]


class ArXivNewPlugin_Replacements(ArXivNewPlugin):
    @staticmethod
    def FilterItems(item, list_):
        return not item["new"]
