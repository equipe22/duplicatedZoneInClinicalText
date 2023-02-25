import json
from pathlib import Path
from pprint import pprint

import pytest

from hegpdup import FingerprintBuilder, DuplicateFinder, TreeBackend

_TEST_CASES_DIR = Path(__file__).parent / "test_cases"
_TEST_CASES_FILES = sorted(_TEST_CASES_DIR.glob("*.json"))


def _getDuplicatesData(duplicates, docIdTo, docText):
    duplicatesData = []
    for duplicate in duplicates:
        text = docText[duplicate.targetSpan.start : duplicate.targetSpan.end]
        duplicate_data = {
            "source_doc_id": duplicate.sourceDocId,
            "target_doc_id": docIdTo,
            "source_start": duplicate.sourceSpan.start,
            "source_end": duplicate.sourceSpan.end,
            "target_start": duplicate.targetSpan.start,
            "target_end": duplicate.targetSpan.end,
            "text": text,
        }
        duplicatesData.append(duplicate_data)
    return duplicatesData


@pytest.mark.parametrize("treeBackend", TreeBackend)
@pytest.mark.parametrize(
    "testCaseFile",
    _TEST_CASES_FILES,
    ids=[f.name for f in _TEST_CASES_FILES],
)
def test_main(treeBackend, testCaseFile):
    with open(testCaseFile) as fp:
        testCase = json.load(fp)

    fingerprintLength = testCase["settings"]["fingerprint_length"]
    orf = testCase["settings"]["orf"]
    minDuplicateLength = testCase["settings"]["min_duplicate_length"]

    fingerprintBuilder = FingerprintBuilder([fingerprintLength], orf)
    duplicateFinder = DuplicateFinder(
        fingerprintBuilder,
        minDuplicateLength=minDuplicateLength,
        treeBackend=treeBackend,
    )

    duplicatesData = []

    for doc_data in testCase["docs"]:
        docIdTo = doc_data["id"]
        docText = doc_data["text"]
        duplicates = duplicateFinder.findDuplicates(docIdTo, docText)
        duplicatesData += _getDuplicatesData(duplicates, docIdTo, docText)

    pprint(duplicatesData, sort_dicts=False)

    if not testCase.get("failing", False):
        assert duplicatesData == testCase["duplicates"]
