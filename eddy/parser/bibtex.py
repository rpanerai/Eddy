try:
    import bibtexparser
    withbibtex = True
except ModuleNotFoundError:
    print('bibtexparser module not found, using regexp')
    import re
    withbibtex = False


class BibtexParser:
    """Class for parsing .bib files"""
    def __init__(self):
        if withbibtex:
            pass
        else:
            pass

