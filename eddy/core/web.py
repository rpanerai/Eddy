import re

from eddy.network.inspire import InspirePlugin
from eddy.network.arxiv import (
    ArXivPlugin, ArXivPlugin_New, ArXivPlugin_NewWithCrossLists, ArXivPlugin_NewAll
)

from eddy.icons import icons


class WebSource:
    def __init__(
            self, name, plugin, icon,
            query_map=lambda x: x, title_gen=lambda x: x,
            has_cites=False):
        self.name = name
        self.plugin = plugin
        self.icon = icon
        self._query_map = query_map
        self._title_gen = title_gen
        self.has_cites = has_cites

    def CreateSearch(self, query):
        query = self._query_map(query)
        title = self._title_gen(query)
        return WebSearch(self, query, title)


class WebSearch:
    def __init__(self, source, query, title):
        self.source = source
        self.query = query
        self.title = title


INSPIRE_SOURCE = WebSource("INSPIRE", InspirePlugin, icons.INSPIRE, has_cites=True)
ARXIV_SOURCE = WebSource("arXiv Search", ArXivPlugin, icons.ARXIV)
ARXIV_NEW_SOURCE = WebSource("arXiv New", ArXivPlugin_New, icons.ARXIV,
    title_gen=lambda x: "new: " + x)


def AddACCap(query, cap):
    if re.search(r"(^|\s)(ac|authorcount)(\W|$)", query):
        return query
    return query + " and " + cap


WEB_SOURCES = [
    INSPIRE_SOURCE,
    ARXIV_SOURCE,
    ARXIV_NEW_SOURCE
]


CHILD_SOURCES = {
    "INSPIRE": [
        WebSource("ac < 10", InspirePlugin, icons.INSPIRE,
            query_map=lambda x: AddACCap(x, "ac<10"), has_cites=True)
    ],
    "arXiv Search": [],
    "arXiv New": [
        WebSource("+ Cross-Lists", ArXivPlugin_NewWithCrossLists, icons.ARXIV,
            title_gen=lambda x: "new: " + x),
        WebSource("All", ArXivPlugin_NewAll, icons.ARXIV,
            title_gen=lambda x: "new: " + x)
    ]
}


# Check that all sources have a unique name
assert (lambda x: len(x) == len(set(x)))(
    [s.name for s in WEB_SOURCES] + [s.name for d in CHILD_SOURCES.values() for s in d]
)
