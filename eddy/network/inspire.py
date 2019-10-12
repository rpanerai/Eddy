import urllib.parse
import json

from PySide2.QtCore import QUrl
from PySide2.QtNetwork import QNetworkRequest


class InspirePlugin():
    @staticmethod
    def CreateRequest(search_string, batch_size, page):
        url = (
            "https://labs.inspirehep.net/api/literature?sort=mostrecent"
            + "&q=" + urllib.parse.quote(search_string)
            + "&size=" + str(batch_size)
            + "&page=" + str(page)
        )
        request = QNetworkRequest(QUrl(url))
        request.setRawHeader(b"Accept", b"application/json")

        return request

    @staticmethod
    def DecodeBatch(reply_string, base_id):
        raw_data = json.loads(reply_string)
        data = [{
            "id": i + base_id,
            "type": (
                InspirePlugin._TYPES.get(d["metadata"]["document_type"][0], "")
                if "document_type" in d["metadata"]
                else ""
            ),
            # "date": d["metadata"]["legacy_creation_date"],
            "date": d["metadata"]["earliest_date"],
            "authors": [
                a["full_name"]
                for a in d["metadata"]["authors"]
            ] if "authors" in d["metadata"] else [],
            "title": d["metadata"]["titles"][0]["title"],
            "abstract": (
                d["metadata"]["abstracts"][0]["value"]
                if "abstracts" in d["metadata"]
                else ""
            ),
            "citations": d["metadata"]["citation_count"],
            "journal": (
                InspirePlugin._DecodeJournal(
                    d["metadata"]["publication_info"][0]
                )
                if "publication_info" in d["metadata"]
                else ""
            ),
            "inspire_id": d["id"],
            "texkey": (
                d["metadata"]["texkeys"][0]
                if "texkeys" in d["metadata"]
                else ""
            ),
            "arxiv_id": (
                d["metadata"]["arxiv_eprints"][0]["value"]
                if "arxiv_eprints" in d["metadata"]
                else ""
            ),
            "dois": list({
                i["value"]
                for i in d["metadata"]["dois"]
            }) if "dois" in d["metadata"] else []
        } for (i, d) in enumerate(raw_data["hits"]["hits"])]

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

        return ""
