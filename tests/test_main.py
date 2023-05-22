import json
from pathlib import Path
from pprint import pprint

import pytest

from duplicatefinder import (
    CharFingerprintBuilder,
    WordFingerprintBuilder,
    DuplicateFinder,
    TreeBackend,
)

_TEST_CASES_DIR = Path(__file__).parent / "test_cases"
_TEST_CASES_FILES = sorted(_TEST_CASES_DIR.glob("*.json"))


def _getDuplicatesData(duplicates, targetDocId, targetDocText):
    duplicatesData = []
    for duplicate in duplicates:
        text = targetDocText[duplicate.targetSpan.start : duplicate.targetSpan.end]
        duplicate_data = {
            "source_doc_id": duplicate.sourceDocId,
            "target_doc_id": targetDocId,
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

    fingerprintType = testCase["settings"]["fingerprint_type"]
    fingerprintLength = testCase["settings"]["fingerprint_length"]
    minDuplicateLength = testCase["settings"]["min_duplicate_length"]

    if fingerprintType == "char":
        fingerprintBuilder = CharFingerprintBuilder(fingerprintLength)
    else:
        assert fingerprintType == "word"
        fingerprintBuilder = WordFingerprintBuilder(fingerprintLength)

    duplicateFinder = DuplicateFinder(
        fingerprintBuilder,
        minDuplicateLength=minDuplicateLength,
        treeBackend=treeBackend,
    )

    duplicatesData = []

    for docData in testCase["docs"]:
        id = docData["id"]
        text = docData["text"]
        duplicates = duplicateFinder.findDuplicates(id, text)
        duplicatesData += _getDuplicatesData(duplicates, id, text)

    pprint(duplicatesData, sort_dicts=False)

    assert duplicatesData == testCase["duplicates"]
