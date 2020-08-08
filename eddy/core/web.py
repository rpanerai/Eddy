from types import SimpleNamespace


class WebSource:
    def __init__(self, name, plugin, icon, query_map=lambda x: x):
        self.name = name
        self.icon = icon
        self.query_map = query_map
        self.plugin = plugin

    def CreateSearch(self, query):
        query = self.query_map(query)
        return WebSearch(self.icon, query, self.plugin)


# class SearchSource:
#     def __init__(self, name, web_source, query):
#         self.name = name
#         self.web_source = web_source
#         self.query = query


class WebSearch(SimpleNamespace):
    def __init__(self, icon, query, plugin):
        super().__init__(icon=icon, query=query, plugin=plugin)


class SearchRequest(SimpleNamespace):
    # The argument source contains the string associated with a key in SourceModel.WEB_SOURCES
    def __init__(self, source, query):
        super().__init__(source=source, query=query)
