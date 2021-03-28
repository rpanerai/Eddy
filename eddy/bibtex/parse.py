import re

# Common substitutions
diacritics = {
    r"\'e": "é", r"\'E": "É",
    r"\`e": "è", r"\`E": "È",
    r'\"a': "ä", r'\"A': "Ä",
    r"\aa": "å", r"\AA": "Å",
    r'\"o': "ö", r'\"O': "Ö",
    r'\"U': "Ü", r'\"u': "ü",
    r"\~n": "ñ", r"\~N": "Ñ",
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
        self.message = f"Could not parse {field} in:"
        for line in entry.split("\n"):
            self.message += "\n\t" + line
        super().__init__(self.message)


def ParseField(key, val):
    """Parses a single field of the form key = val"""

    new_key = key.strip(" \n\t")

    # # Handle only the keys that we need
    # if new_key not in [
    #     "title", "author", "eprint", "abstract",
    #     "date", "journal", "volume", "number", "issue", "pages", "year",
    #     "doi", "isbn", "publisher", "url", "school", "series", "edition"
    # ]:
    #     return {}

    # Remove whitespaces
    new_val = re.sub(r"\s+", lambda m: "" if m.start(0) == 0 or m.end(0) == len(val) else " ", val)

    # Here we remove the top-level "...", {...} or "{...}" wrapping the entry
    # Note that we want to transform "{aa}cc{bb}" to {aa}cc{bb} and not aa}cc{bb
    temp = None
    loops = 0
    while temp != new_val:
        temp = new_val
        loops += 1
        depth = 1
        if not new_val:
            break
        elif new_val[0] == '"':
            closing_token = '"'
            opening_token = '"'
        elif new_val[0] == "{":
            closing_token = "}"
            opening_token = "{"
        else:
            if loops == 1:
                raise ParseError(new_key, f"{new_key} = {new_val}")
            else:
                break
        escape = False
        for count, char in enumerate(new_val[1:]):
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == closing_token:
                depth -= 1
            elif char == opening_token:
                depth += 1
            if depth == 0:
                if count == len(new_val)-2:
                    new_val = new_val[1:-1]
                else:
                    if loops == 1:
                        raise ParseError(new_key, f"{new_key} = {new_val}")
                    else:
                        break

    for tex, char in diacritics.items():
        new_val = new_val.replace(tex, char)

    # The authors, separated by "and", are parsed into a list of tuples [(last name, name), ... ]
    if new_key == "author":
        and_pos = [(0, None)]
        depth = 0
        escape = False

        # We need again to loop because we want to ignore any and inside braces
        for count, char in enumerate(new_val):
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
            elif char == " " and depth == 0:
                if new_val[count:count+5] == " and ":
                    and_pos[-1] = (and_pos[-1][0], count)
                    and_pos.append((count+5, None))

        author_list = []
        for pos_i, pos_f in and_pos:
            author_list.append(
                tuple(re.sub("[}{]", "", new_val[pos_i:pos_f]).split(", ", 1))
            )

        return {new_key: author_list}

    return {new_key: new_val}


def ParseEntry(entry):
    """Parses a single bibtex entry and returns a dict"""

    output_dict = {}

    full_match = re.match(r"\s*@([A-Za-z]\w*){([^,]+),(.*)}\s*$", entry, re.DOTALL)
    if full_match:
        if full_match.group(1) == "COMMENT":
            return None

        output_dict.update({"type": full_match.group(1), "id": full_match.group(2)})

        # Runs through all entries by finding the positions of the equal signs
        # It ignores those equals that are inside {} or "", handling also escapes
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

        if brace_depth != 0:
            raise ParseError("matching braces", fields)
        if quotes:
            raise ParseError("matching quotes", fields)

        try:
            if comma_pos[-1] < equal_pos[-1]:
                comma_pos.append(None)

            for order, pos in enumerate(comma_pos[:-1]):
                output_dict.update(
                    ParseField(fields[pos+1:equal_pos[order]],
                               fields[equal_pos[order]+1:comma_pos[order+1]])
                )

        except IndexError:
            raise ParseError("content", fields)

    else:
        raise ParseError("type", entry)

    return output_dict


def ParseBibtex(content):
    """Parses a bibtex string and returns a database"""

    uncommented_content = re.sub("^%.*$", "", content, re.MULTILINE)

    # Returns an iterator over all bibtex entries, all starting with @
    match_entry = re.finditer(r"@([A-Za-z]\w*){", uncommented_content)
    entry_list = []
    positions_list = []

    for entry in match_entry:
        positions_list.append(entry.start(0))

    for start, end in zip(positions_list, [*positions_list[1:], None]):
        text = uncommented_content[start:end]

        try:
            parsed = ParseEntry(text)
        except ParseError as e:
            # For now we silently pass
            print(e)
        else:
            if parsed is not None:
                entry_list.append(parsed)

    return entry_list

