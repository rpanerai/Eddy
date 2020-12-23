from types import SimpleNamespace

from eddy.network.inspire import InspirePlugin
from eddy.network.arxiv import ArXivPlugin, ArXivNewPlugin

from eddy.icons import icons


class WebSource:
    def __init__(self, name, plugin, icon, query_map=lambda x: x):
        self.name = name
        self.plugin = plugin
        self.icon = icon
        self.query_map = query_map

    def CreateSearch(self, query):
        query = self.query_map(query)
        return WebSearch(self, query)


# class SearchSource(SimpleNamespace):
#     def __init__(self, name, plugin, icon, query=None):
#         super().__init__(name=name, plugin=plugin, icon=icon, query=query)


class WebSearch(SimpleNamespace):
    def __init__(self, source, query):
        super().__init__(source=source, query=query)


INSPIRE_SOURCE = WebSource("INSPIRE", InspirePlugin, icons.INSPIRE)
ARXIV_SOURCE = WebSource("arXiv", ArXivPlugin, icons.ARXIV)


WEB_SOURCES = [
    INSPIRE_SOURCE,
    ARXIV_SOURCE
]
assert (lambda x: len(x) == len(set(x)))([s.name for s in WEB_SOURCES])


CHILD_SOURCES = {
    "arXiv": [
        WebSource("new", ArXivNewPlugin, icons.ARXIV)
    ]
}
