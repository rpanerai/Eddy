import urllib.parse
import json

from PySide2.QtCore import QUrl
from PySide2.QtNetwork import QNetworkRequest
from eddy.network.fetcher import Callback


class InspirePlugin:
    BATCH_SIZE = 50

    class Status:
        def __init__(self, search_string, page):
            self.search_string = search_string
            self.page = page

    @staticmethod
    def Start(search_string):
        status = InspirePlugin.Status(search_string, 1)
        request = InspirePlugin._CreateRequest(status)

        return (status, Callback([], request))

    @staticmethod
    def HandleReply(status, reply_string):
        raw_data = json.loads(reply_string)
        data = [InspirePlugin._DecodeEntry(d) for d in raw_data["hits"]["hits"]]

        total = raw_data["hits"]["total"]

        if total > status.page * InspirePlugin.BATCH_SIZE:
            status.page = status.page + 1
            return (status, Callback(data, InspirePlugin._CreateRequest(status)))
        else:
            return (None, Callback(data, None))

    _TYPES = {
        "article": "A",
        "book": "B",
        "book chapter": "C",
        "note": "N",
        "conference paper": "P",
        "proceedings": "P",
        "report": "R",
        "activity report": "R",
        "thesis": "T"
    }

    @staticmethod
    def _CreateRequest(status):
        url = (
            f"https://inspirehep.net/api/literature?sort=mostrecent"
            f"&q={urllib.parse.quote(status.search_string)}"
            f"&size={InspirePlugin.BATCH_SIZE}"
            f"&page={status.page}"
        )
        request = QNetworkRequest(QUrl(url))
        request.setRawHeader(b"Accept", b"application/json")

        return request

    @staticmethod
    def _DecodeJournal(pub_info):
        output = {}

        if "journal_title" in pub_info:
            output["publication"] = pub_info["journal_title"]
        elif "pubinfo_freetext" in pub_info:
            output["publication"] = pub_info["pubinfo_freetext"]

        if "journal_volume" in pub_info:
            output["volume"] = pub_info["journal_volume"]

        if "year" in pub_info:
            output["year"] = pub_info["year"]

        if "journal_issue" in pub_info:
            output["issue"] = pub_info["journal_issue"]

        if "page_start" in pub_info:
            pages = pub_info["page_start"]
            if "page_end" in pub_info:
                pages = f"{pages}-{pub_info['page_end']}"
        elif "artid" in pub_info:
            pages = pub_info["artid"]
        else:
            return output

        output["pages"] = pages
        return output

    @staticmethod
    def _DecodeBook(data):
        output = {}

        if "imprints" in data:
            publisher = data["imprints"][0].get("publisher", None)
            if publisher is not None:
                output["publisher"] = publisher

        if "isbns" in data:
            output["isbns"] = [i["value"] for i in data["isbns"]]

        if "book_series" in data:
            if "title" in data["book_series"][0]:
                output["series"] = data["book_series"][0]["title"]
            if "volume" in data["book_series"][0]:
                output["volume"] = data["book_series"][0]["volume"]

        return output

    @staticmethod
    def _DecodeThesis(thesis):
        output = {}

        if "degree_type" in thesis:
            output["degree"] = thesis["degree_type"]

        if "institutions" in thesis:
            output["institution"] = thesis["institutions"][0]["name"]

        if "date" in thesis:
            try:
                output["year"] = int(thesis["date"].split("-")[0])
            except:
                pass

        return output

    @staticmethod
    def _DecodeArXiv(eprint):
        output = {}

        output["arxiv_id"] = eprint["value"]

        if "categories" in eprint:
            output["arxiv_cats"] = eprint["categories"]

        return output

    @staticmethod
    def _DecodeEntry(entry):
        item = {}
        data = entry["metadata"]

        if "document_type" in data:
            item["type"] = InspirePlugin._TYPES.get(data["document_type"][0], "A")

        item["date"] = data["earliest_date"]

        # if "authors" in data:
        #     item["authors"] = [a["full_name"] for a in data["authors"]]
        authors = []
        authors_bais = []
        editors = []
        editors_bais = []
        for a in data.get("authors", []):
            if "editor" in a.get("inspire_roles", []):
                editors.append(a["full_name"])
                editors_bais.append(next(
                    (i for i in a.get("ids", dict()) if i["schema"] == "INSPIRE BAI"),
                    dict()).get("value", None))
            else:
                authors.append(a["full_name"])
                authors_bais.append(next(
                    (i for i in a.get("ids", dict()) if i["schema"] == "INSPIRE BAI"),
                    dict()).get("value", None))
        if authors != []:
            item["authors"] = authors
            item["authors_bais"] = authors_bais
        if editors != []:
            item["editors"] = editors
            item["editors_bais"] = editors_bais

        item["title"] = data["titles"][0]["title"]
        # item["title"] = next(
        #     (t["title"] for t in data["titles"] if "<math display=" not in t["title"]))

        if "abstracts" in data:
            item["abstract"] = (data["abstracts"][0]["value"])
            # item["abstract"] = next(
            #     (t["value"] for t in data["abstracts"] if "<math display=" not in t["value"]))

        item["citations"] = data["citation_count"]

        if "publication_info" in data:
            item.update(InspirePlugin._DecodeJournal(data["publication_info"][0]))

        item.update(InspirePlugin._DecodeBook(data))

        if "thesis_info" in data:
            item.update(InspirePlugin._DecodeThesis(data["thesis_info"]))

        item["inspire_id"] = entry["id"]

        if "texkeys" in data:
            item["texkey"] = data["texkeys"][0]

        if "arxiv_eprints" in data:
            item.update(InspirePlugin._DecodeArXiv(data["arxiv_eprints"][0]))

        if "dois" in data:
            item["dois"] = list({i["value"] for i in data["dois"]})

        return item


class InspireBibTeXPlugin:
    @staticmethod
    def Start(search_string):
        url = (
            f"https://inspirehep.net/api/literature?"
            f"&q={urllib.parse.quote(search_string)}"
            f"&size=1"
            f"&format=bibtex"
        )
        request = QNetworkRequest(QUrl(url))
        request.setRawHeader(b"Accept", b"application/x-bibtex")

        return (None, Callback([], request))

    @staticmethod
    def HandleReply(status, reply_string):
        return (None, Callback(reply_string.split("\n\n"), None))
