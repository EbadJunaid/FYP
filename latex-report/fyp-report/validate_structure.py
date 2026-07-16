"""Lightweight structural checks for the report when a TeX engine is unavailable."""

from __future__ import print_function

import io
import os
import re
import sys


ROOT = os.path.dirname(os.path.abspath(__file__))
TEX_FILES = []
for directory, _, filenames in os.walk(ROOT):
    TEX_FILES.extend(
        os.path.join(directory, filename)
        for filename in filenames
        if filename.endswith(".tex")
    )
TEX_FILES.sort()
ERRORS = []


def read_text(path):
    with io.open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def without_comments(source):
    """Remove unescaped TeX comments before structural pattern checks."""
    return re.sub(r"(?<!\\)%.*", "", source)


for path in TEX_FILES:
    source = read_text(path)
    depth = 0
    escaped = False
    for character in source:
        if escaped:
            escaped = False
            continue
        if character == chr(92):
            escaped = True
        elif character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth < 0:
                ERRORS.append("{}: unexpected closing brace".format(os.path.basename(path)))
                break
    if depth != 0:
        ERRORS.append("{}: brace depth {}".format(os.path.basename(path), depth))

    structural_source = without_comments(source)
    beginnings = re.findall(r"\\begin\{([^}]+)\}", structural_source)
    endings = re.findall(r"\\end\{([^}]+)\}", structural_source)
    if sorted(beginnings) != sorted(endings):
        ERRORS.append("{}: environment mismatch".format(os.path.basename(path)))


main = read_text(os.path.join(ROOT, "main.tex"))
for included in re.findall(r"\\input\{([^}]+)\}", main):
    candidate = os.path.join(ROOT, included if included.endswith(".tex") else included + ".tex")
    if not os.path.exists(candidate):
        ERRORS.append("missing input: {}".format(included))


all_tex = "\n".join(read_text(path) for path in TEX_FILES)
labels = set(re.findall(r"\\label\{([^}]+)\}", all_tex))
references = set(re.findall(r"\\(?:ref|pageref|autoref)\{([^}]+)\}", all_tex))
if references - labels:
    ERRORS.append("undefined references: " + ", ".join(sorted(references - labels)))


bibliography = read_text(os.path.join(ROOT, "references.bib"))
bibliography_keys = set(re.findall(r"@\w+\{([^,]+),", bibliography))
citation_keys = set()
for group in re.findall(r"\\cite\{([^}]+)\}", all_tex):
    citation_keys.update(key.strip() for key in group.split(","))
if citation_keys - bibliography_keys:
    ERRORS.append("undefined citations: " + ", ".join(sorted(citation_keys - bibliography_keys)))


chapters_directory = os.path.join(ROOT, "chapters")
chapters = sorted(
    filename for filename in os.listdir(chapters_directory) if filename.endswith(".tex")
)
if chapters != ["chapter1.tex", "chapter2.tex", "chapter3.tex", "chapter4.tex", "chapter5.tex", "chapter6.tex", "chapter7.tex", "chapter8.tex", "chapter9.tex"]:
    ERRORS.append("chapter boundary violated: {!r}".format(chapters))

numbered_chapters = re.findall(r"\\chapter\{([^}]+)\}", all_tex)
if numbered_chapters != [
    "Introduction",
    "Technical Background and Related Work",
    "Requirements and System Analysis",
    "System Architecture and Data Design",
    "Certificate Acquisition and Dataset Construction",
    "Certificate Transparency Renewal and Discovery Pipeline",
    "Certificate Analytics and Dashboard",
    "Evaluation, Security, and Limitations",
    "Conclusion and Future Work",
]:
    ERRORS.append("unexpected numbered chapters: {!r}".format(numbered_chapters))


if ERRORS:
    print("FAIL")
    print("\n".join(ERRORS))
    sys.exit(1)

print(
    "PASS: {} TeX files; {} labels; {} citations; chapters={}".format(
        len(TEX_FILES), len(labels), len(citation_keys), chapters
    )
)
