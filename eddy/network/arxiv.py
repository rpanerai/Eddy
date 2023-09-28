import itertools
import urllib.parse
import feedparser

from PySide2.QtCore import QUrl
from PySide2.QtNetwork import QNetworkRequest
from eddy.network.fetcher import Callback


def AbstractUrl(arxiv_id):
    return f"https://arxiv.org/abs/{arxiv_id}"


def PDFUrl(arxiv_id):
    return f"https://arxiv.org/pdf/{arxiv_id}.pdf"


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
    def _CreateRequest(status):
        url = (
            f"https://export.arxiv.org/api/query?"
            f"search_query={urllib.parse.quote(status.search_string)}"
            f"&start={status.last_n}"
            f"&max_results={ArXivPlugin.BATCH_SIZE}"
            f"&sortBy=submittedDate&sortOrder=descending"
        )
        request = QNetworkRequest(QUrl(url))

        return request

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


class ArXivPlugin_New(ArXivPlugin):
    CATEGORIES = (
        "astro-ph",
        "cond-mat",
        "cs",
        "econ",
        "eess",
        "gr-qc",
        "hep-ex",
        "hep-lat",
        "hep-ph",
        "hep-th",
        "math",
        "math-ph",
        "nlin",
        "nucl-ex",
        "nucl-th",
        "physics",
        "q-bio",
        "q-fin",
        "quant-ph",
        "stat"
    )

    class Status:
        def __init__(self, categories, last_n):
            self.ids = dict((c, None) for c in categories)
            self.search_string = None
            self.last_n = last_n

    @staticmethod
    def Start(search_string):
        categories = search_string.replace(","," ").split()
        categories = [c for c in categories if c in ArXivPlugin_New.CATEGORIES]

        if categories == []:
            return (None, Callback([], None))

        status = ArXivPlugin_New.Status(categories, 0)
        request = ArXivPlugin_New._CreateRSSRequest(status)

        return (status, Callback([], request))

    @classmethod
    def HandleReply(cls, status, reply_string):
        if status.search_string is not None:
            return ArXivPlugin.HandleReply(status, reply_string)

        status.ids.update(cls._DecodeRSSRequest(reply_string))
        if None in status.ids.values():
            request = ArXivPlugin_New._CreateRSSRequest(status)
            return (status, Callback([], request))
        else:
            ids = set(itertools.chain.from_iterable(status.ids.values()))
            status.search_string = ",".join(ids)
            request = ArXivPlugin_New._CreateRequest(status)
            return (status, Callback([], request))


    @staticmethod
    def _CreateRSSRequest(status):
        for (c,l) in status.ids.items():
            if l is None:
                break

        url = f"https://export.arxiv.org/rss/{c}"
        request = QNetworkRequest(QUrl(url))
        return request

    @staticmethod
    def _CreateRequest(status):
        url = (
            f"https://export.arxiv.org/api/query?"
            f"id_list={urllib.parse.quote(status.search_string)}"
            f"&start={status.last_n}"
            f"&max_results={ArXivPlugin.BATCH_SIZE}"
        )
        request = QNetworkRequest(QUrl(url))
        return request

    @classmethod
    def _DecodeRSSRequest(cls, reply_string):
        raw_data = feedparser.parse(reply_string)
        category = raw_data["feed"]["title"].split(" ")[0]
        news = [
            {"id": i["title"].split(":")[-1].split(" ")[0],
            "list": i["title"].split("[")[-1].split("]")[0],
            "new": i["title"][-8:-1] != "UPDATED"}
            for i in raw_data["entries"]
        ]
        news = [d for d in news if cls._FilterItems(d, category)]
        return {category: [i["id"] for i in news]}

    @staticmethod
    def _FilterItems(item, list_):
        return item["list"] == list_ and item["new"]


class ArXivPlugin_NewWithCrossLists(ArXivPlugin_New):
    @staticmethod
    def _FilterItems(item, list_):
        return item["new"]


class ArXivPlugin_NewAll(ArXivPlugin_New):
    @staticmethod
    def _FilterItems(item, list_):
        return True
