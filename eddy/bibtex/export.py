

def BibtexFromDB(table, ids):
    """Builds a bibtex entry from a paper's database entry"""

    output = []
    for id in ids:

        row = table.GetRow(id)

        try:
            if row["type"] == "A":
                entry_type = "article"
            else:
                entry_type = "misc"

            entry_auths = " and ".join(eval(row["authors"]))

            if row["inspire_id"] is None:
                # If the inspire id is missing we take the author and the first 6 digits of the hash
                entry_name = eval(row["authors"])[0].split(",")[0] + ":" + format(hash(str(row)) & 0xffffff, "0x")
                # TO DO: if an author has multiple given names, one should wrap them inside braces
            else:
                entry_name = row["inspire_id"]

            entry_title = row["title"]

            entry_eprint = row.get("arxiv_id", None)
            if entry_eprint:
                entry_eprint = ["\teprint = " + entry_eprint]
            else:
                entry_eprint = []
            # More fields ...

            bib_entry = '\n'.join([
                f"@{entry_type}" + "{" + entry_name + ",",
                f'\ttitle = "{entry_title}",',
                f'\tauthors = "{entry_auths}",',
                # Use the * so that if the entry is unavailable (i.e. []) it is automatically removed
                *entry_eprint,
                "}"
            ])
        except KeyError as e:
            print(f"Key {e} not found in the database. Skipping entry")
        except SyntaxError:
            print("Could not evaluate the entry 'authors'. Skipping entry")
        else:
            output.append(bib_entry)

    return "\n\n".join(output)
