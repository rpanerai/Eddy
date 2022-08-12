from urllib import request
import urllib.parse
import feedparser

from PySide2.QtCore import QUrl
from PySide2.QtNetwork import QNetworkRequest
from eddy.network.fetcher import Callback


class ArXivPlugin():
    BATCH_SIZE = 200

    class Status:
        def __init__(self, search_string, last_n):
            self.search_string = search_string
            self.last_n = last_n

    @staticmethod
    def Start(search_string):
        status = ArXivPlugin.Status(search_string, 0)
        request = ArXivPlugin._CreateRequest(status)

        return (status, Callback([], request))

    @staticmethod
    def _CreateRequest(status):
        url = (
            "https://export.arxiv.org/api/query?"
            + "search_query=" + urllib.parse.quote(status.search_string)
            + "&start=" + str(status.last_n)
            + "&max_results=" + str(ArXivPlugin.BATCH_SIZE)
            + "&sortBy=submittedDate&sortOrder=descending"
        )
        request = QNetworkRequest(QUrl(url))

        return request

    @staticmethod
    def HandleReply(status, reply_string):
        raw_data = feedparser.parse(reply_string)
        data = [ArXivPlugin._DecodeEntry(d) for d in raw_data["entries"]]

        total = int(raw_data["feed"]["opensearch_totalresults"])
        status.last_n = status.last_n + len(data)

        if total > status.last_n:
            return (status, Callback(data, ArXivPlugin._CreateRequest(status)))
        else:
            return (None, Callback(data, None))

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
        item["arxiv_cats"] = [d["term"] for d in entry["tags"]]

        if "arxiv_doi" in entry:
            item["dois"] = [entry["arxiv_doi"]]

        return item


class ArXivNewPlugin(ArXivPlugin):
    class Status:
        def __init__(self, category, last_n):
            self.category = category
            self.last_n = last_n
            self.ids = None

    @staticmethod
    def Start(search_string):
        status = ArXivNewPlugin.Status(search_string, 0)
        request = ArXivNewPlugin._CreateRSSRequest(status)

        return (status, Callback([], request))

    @classmethod
    def HandleReply(cls, status, reply_string):
        if status.ids is None:
            status.ids = cls._DecodeRSSRequest(reply_string)
            request = ArXivNewPlugin._CreateRequest(status)
            return (status, Callback([], request))
        else:
            return ArXivPlugin.HandleReply(status, reply_string)

    @staticmethod
    def _CreateRSSRequest(status):
        url = "https://export.arxiv.org/rss/" + status.category
        request = QNetworkRequest(QUrl(url))
        return request

    @staticmethod
    def _CreateRequest(status):
        url = (
            "https://export.arxiv.org/api/query?"
            + "id_list=" + urllib.parse.quote(status.ids)
            + "&start=" + str(status.last_n)
            + "&max_results=" + str(ArXivPlugin.BATCH_SIZE)
        )
        request = QNetworkRequest(QUrl(url))
        return request

    @classmethod
    def _DecodeRSSRequest(cls, reply_string):
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
        news = [d for d in news if cls._FilterItems(d, list_)]

        search_string = ",".join([i["id"] for i in news])
        # It could be useful to also pass the size of the batch,
        # size = len(news) + 1
        return search_string

    @staticmethod
    def _FilterItems(item, list_):
        return True


class ArXivNewPlugin_News(ArXivNewPlugin):
    @staticmethod
    def _FilterItems(item, list_):
        return item["list"] == list_ and item["new"]


class ArXivNewPlugin_CrossLists(ArXivNewPlugin):
    @staticmethod
    def _FilterItems(item, list_):
        return item["list"] != list_ and item["new"]


class ArXivNewPlugin_Replacements(ArXivNewPlugin):
    @staticmethod
    def _FilterItems(item, list_):
        return not item["new"]
