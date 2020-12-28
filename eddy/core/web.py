from eddy.network.inspire import InspirePlugin
from eddy.network.arxiv import (
    ArXivPlugin, ArXivNewPlugin_News, ArXivNewPlugin_CrossLists, ArXivNewPlugin_Replacements
)

from eddy.icons import icons


class WebSource:
    def __init__(self, name, plugin, icon, query_map=lambda x: x, title_gen=lambda x: x):
        self.name = name
        self.plugin = plugin
        self.icon = icon
        self._query_map = query_map
        self._title_gen = title_gen

    def CreateSearch(self, query):
        query = self._query_map(query)
        title = self._title_gen(query)
        return WebSearch(self, query, title)


class WebSearch:
    def __init__(self, source, query, title):
        self.source = source
        self.query = query
        self.title = title


INSPIRE_SOURCE = WebSource("INSPIRE", InspirePlugin, icons.INSPIRE)
ARXIV_SOURCE = WebSource("arXiv", ArXivPlugin, icons.ARXIV)


WEB_SOURCES = [
    INSPIRE_SOURCE,
    ARXIV_SOURCE
]


CHILD_SOURCES = {
    "arXiv": [
        WebSource("news", ArXivNewPlugin_News, icons.ARXIV,
            title_gen=lambda x: "news: " + x),
        WebSource("cross-lists", ArXivNewPlugin_CrossLists, icons.ARXIV,
            title_gen=lambda x: "cross-lists: " + x),
        WebSource("replacements", ArXivNewPlugin_Replacements, icons.ARXIV,
            title_gen=lambda x: "replacements: " + x)
    ]
}


# Check that all sources have a unique name
assert (lambda x: len(x) == len(set(x)))(
    [s.name for s in WEB_SOURCES] + [s.name for d in CHILD_SOURCES.values() for s in d]
)
