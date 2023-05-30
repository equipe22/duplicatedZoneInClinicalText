# Duplicate Text Finder

A python library to detect duplicated zones in text. Primarily meant to detect
copy/paste across medical documents. Should be faster than python's built-in
`difflib` algorithm and more robust to whitespace, newlines and other irrelevant
characters.

## Usage

```python3

from pathlib import Path
from duptextfinder import CharFingerprintBuilder, DuplicateFinder

# load some text files
texts = [p.read_text() for p in Path("some/dir").glob("*.txt")]

# init fingerprint and duplicate finder
fingerprintBuilder = CharFingerprintBuilder(fingerprintLength=15)
duplicateFinder = DuplicateFinder(fingerprintBuilder, minDuplicateLength=15)

# call findDuplicates() on each file
for i, text in enumerate(texts):
    id = f"D{i}"
    duplicates = duplicateFinder.findDuplicates(id, text)
    for duplicate in duplicates:
        print(
            f"sourceDoc={duplicate.sourceDocId}, "
            f"sourceStart={duplicate.sourceSpan.start}, "
            f"sourceEnd={duplicate.sourceSpan.end}, "
            f"targetStart={duplicate.targetSpan.start}, "
            f"targetEnd={duplicate.targetSpan.end}"
        )
        duplicated_text = text[duplicate.targetSpan.start : duplicate.targetSpan.end]
        print(duplicated_text)
```

`WordFingerprintBuilder` can be used instead of `CharFingerprintBuilder`. For
more details, refer to the docstrings of `DuplicateFinder`,
`CharFingerprintBuilder` and `WordFingerprintBuilder`.

## How to run tests

1. Install package in editable mode with test and extra dependencies by running `pip install -e ".[tests, ncls, intervaltree]"` in the repo directory
2. Launch `pytest tests/`

## About ncls and intervaltree

This tool can be used without any additional dependencies, but performance can
be improved when using interval trees. To benefit from this you well need to
install either the [ncls](https://github.com/biocore-ntnu/ncls) package or the
[intervaltree](https://github.com/chaimleib/intervaltree) package.


## References
- Evaluating the Impact of Text Duplications on a Corpus of More than 600,000 Clinical Narratives in a French Hospital. https://www.hal.inserm.fr/hal-02265124/
