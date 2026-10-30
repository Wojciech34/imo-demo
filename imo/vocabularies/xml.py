"""The reserved XML namespace and its four standard attribute names.

Constants only, with no parser dependency. Each adapter decides which of these
attributes it accepts and how it handles their scope and values.
"""

XML = "http://www.w3.org/XML/1998/namespace"

BASE = f"{{{XML}}}base"
LANG = f"{{{XML}}}lang"
SPACE = f"{{{XML}}}space"
ID = f"{{{XML}}}id"
