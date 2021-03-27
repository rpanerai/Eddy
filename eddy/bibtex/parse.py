import re
from itertools import tee

diacritics = {
    r"\'e": "é", r"\'E": "É",
    r"\`e": "è", r"\`E": "È",
    r'\"a': "ä", r'\"A': "Ä",
    r"\aa": "å", r"\AA": "Å",
    r'\"o': "ö", r'\"O': "Ö",
    r'\"U': "Ü", r'\"u': "ü",
    r"\~n": "ñ",
    r"\'c": "ć", r"\'C": "Ć",
    r"\u g": "ğ", r"\u{g}": "ğ",
    r"\v c": "č", r"\v{c}": "č", r"\v C": "Č", r"\v{C}": "Č",
    r"\'o": "ó", r"\'O": "Ó",
    r"\o": "ø", r"\O": "Ø",
    r"\l": "ł", r"\L": "Ł",
    r"\_": "_",
    r"\c c": "ç", r"\c{c}": "ç"
}


class ParseError(Exception):
    """Exception raised when the bibtex does not parse"""

    def __init__(self, field, entry):
        self.message = f"Could not parse the {field} in:"
        for line in entry.split("\n"):
            self.message += "\n\t" + line
        super().__init__(self.message)


def parseField(key, val):
    """Parses a single field of the form key = val"""

    new_key = key.strip()
    new_val = re.sub(r"\s+", lambda m: "" if m.start(0) == 0 or m.end(0) == len(val) else " ", val)

    if new_key == "title":
        pass
    elif new_key == "author":
        for tex, char in diacritics.items():
            new_val = new_val.replace(tex, char)

    return {new_key: new_val}


def parseEntry(entry):
    """Parses a single bibtex entry and returns a dict"""

    output_dict = {}

    full_match = re.match(r"\s*@([A-Za-z]\w*){([^,]+),(.*)}\s*$", entry, re.DOTALL)
    if full_match:
        output_dict.update({"type": full_match.group(1), "id": full_match.group(2)})

        brace_depth = 0
        quotes = False
        escape = False
        fields = full_match.group(3)
        comma_pos = [-1]
        equal_pos = []
        for pos, char in enumerate(fields):
            if escape:
                escape = False
            elif brace_depth == 0 and not quotes:
                if char == "{":
                    brace_depth += 1
                elif char == '"':
                    quotes = True
                elif char == "=":
                    equal_pos.append(pos)
                elif char == ",":
                    comma_pos.append(pos)
                elif char == "\\":
                    escape = True
            elif quotes:
                if char == '"':
                    quotes = False
                elif char == "{":
                    brace_depth += 1
                elif char == "}":
                    brace_depth -= 1
                elif char == "\\":
                    escape = True
            elif brace_depth > 0:
                if char == '"':
                    quotes = True
                if char == "}":
                    brace_depth -= 1
                elif char == "{":
                    brace_depth += 1
                elif char == "\\":
                    escape = True
        try:
            if comma_pos[-1] > equal_pos[-1]:
                comma_pos[-1] = None
            else:
                comma_pos.append(None)

            for order, pos in enumerate(comma_pos[:-1]):
                output_dict.update(
                    parseField(fields[pos+1:equal_pos[order]],
                               fields[equal_pos[order]+1:comma_pos[order+1]])
                )

        except IndexError:
            raise ParseError("content", fields)

    else:
        raise ParseError("type", entry)

    return output_dict


def parseBibtex(content):
    """Parses a bibtex string and returns a database"""

    match_entry = re.finditer(r"@([A-Za-z]\w*){", content)
    entry_list = []
    positions_list = []

    for entry in match_entry:
        positions_list.append(entry.start(0))

    for start, end in zip(positions_list, [*positions_list[1:], None]):
        text = content[start:end]

        try:
            parsed = parseEntry(text)
        except ParseError as e:
            # For now we silently pass
            print(e)
        else:
            entry_list.append(parsed)

    return entry_list

