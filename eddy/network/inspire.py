import urllib.parse
import json

from PySide2.QtCore import QUrl
from PySide2.QtNetwork import QNetworkRequest


class InspirePlugin():
    DEFAULT_BATCH_SIZE = 50

    @staticmethod
    def CreateRequest(search_string, batch_size, page):
        url = (
            "https://inspirehep.net/api/literature?sort=mostrecent"
            + "&q=" + urllib.parse.quote(search_string)
            + "&size=" + str(batch_size)
            + "&page=" + str(page)
        )
        request = QNetworkRequest(QUrl(url))
        request.setRawHeader(b"Accept", b"application/json")

        return request

    @staticmethod
    def DecodeBatch(reply_string):
        raw_data = json.loads(reply_string)
        data = [InspirePlugin._DecodeEntry(d) for d in raw_data["hits"]["hits"]]

        total = raw_data["hits"]["total"]

        return (data, total)

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
                pages = pages + "-" + pub_info["page_end"]
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
                editors_bais.append(a.get("bai", None))
            else:
                authors.append(a["full_name"])
                authors_bais.append(a.get("bai", None))
        if authors != []:
            item["authors"] = authors
            item["authors_bais"] = authors_bais
        if editors != []:
            item["editors"] = editors
            item["editors_bais"] = editors_bais

        item["title"] = data["titles"][0]["title"]

        if "abstracts" in data:
            item["abstract"] = (data["abstracts"][0]["value"])

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
            item["arxiv_id"] = data["arxiv_eprints"][0]["value"]

        if "dois" in data:
            item["dois"] = list({i["value"] for i in data["dois"]})

        return item


class InspireBibTeXPlugin():
    DEFAULT_BATCH_SIZE = 200

    @staticmethod
    def CreateRequest(search_string, batch_size, page):
        url = (
            "https://inspirehep.net/api/literature?"
            + "&q=" + urllib.parse.quote(search_string)
            + "&size=" + str(batch_size)
            + "&page=" + str(page)
            + "&format=bibtex"
        )
        request = QNetworkRequest(QUrl(url))
        request.setRawHeader(b"Accept", b"application/x-bibtex")

        return request

    @staticmethod
    def DecodeBatch(reply_string):
        return (reply_string.split("\n\n"), None)
