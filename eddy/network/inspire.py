import urllib.parse
import json

from PySide2.QtCore import QUrl
from PySide2.QtNetwork import QNetworkRequest


class InspirePlugin():
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
        if "journal_title" in pub_info:
            text = pub_info["journal_title"]
            if "journal_volume" in pub_info:
                text = text + " " + pub_info["journal_volume"]
            if "year" in pub_info:
                text = text + " (" + str(pub_info["year"]) + ")"
            if "journal_issue" in pub_info:
                text = text + " " + pub_info["journal_issue"]
            if "artid" in pub_info:
                text = text + " " + pub_info["artid"]
            return text

        if "pubinfo_freetext" in pub_info:
            return pub_info["pubinfo_freetext"]

        return None

    @staticmethod
    def _DecodeEntry(entry):
        item = {}
        data = entry["metadata"]

        if "document_type" in data:
            item["type"] = InspirePlugin._TYPES.get(data["document_type"][0], None)

        item["date"] = data["earliest_date"]

        if "authors" in data:
            item["authors"] = [a["full_name"] for a in data["authors"]]

        item["title"] = data["titles"][0]["title"]

        if "abstracts" in data:
            item["abstract"] = (data["abstracts"][0]["value"])

        item["citations"] = data["citation_count"]

        if "publication_info" in data:
            item["journal"] = InspirePlugin._DecodeJournal(data["publication_info"][0])

        item["inspire_id"] = entry["id"]

        if "texkeys" in data:
            item["texkey"] = data["texkeys"][0]

        if "arxiv_eprints" in data:
            item["arxiv_id"] = data["arxiv_eprints"][0]["value"]

        if "dois" in data:
            item["dois"] = list({i["value"] for i in data["dois"]})

        return item
