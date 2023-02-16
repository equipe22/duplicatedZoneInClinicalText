import json
from pathlib import Path
from pprint import pprint

import pytest

from hegpdup.fingerprint_builder import FingerprintBuilder
from hegpdup.duplicate_finder import DuplicateFinder

_TEST_CASES_DIR = Path(__file__).parent / "test_cases"
_TEST_CASES_FILES = sorted(_TEST_CASES_DIR.glob("*.json"))


def _extractDuplicatesFromTrees(
    trees,
    docIdTo,
    docText,
    minDuplicateLength,
):
    duplicatesData = []
    for docIdFrom, tree in trees.items():
        seen = set()
        for interval in sorted(tree):
            targetStart = interval.data.start
            targetEnd = interval.data.end

            if (targetEnd - targetStart) < minDuplicateLength:
                continue
            if (targetStart, targetEnd) in seen:
                continue

            text = docText[targetStart:targetEnd]

            duplicatesData.append(
                {
                    "source_doc_id": docIdFrom,
                    "target_doc_id": docIdTo,
                    "source_start": interval.begin,
                    "source_end": interval.end,
                    "target_start": targetStart,
                    "target_end": targetEnd,
                    "text": text,
                }
            )

            seen.add((targetStart, targetEnd))
    return duplicatesData


@pytest.mark.parametrize(
    "testCaseFile", _TEST_CASES_FILES, ids=[f.name for f in _TEST_CASES_FILES]
)
def test_cases(testCaseFile):
    with open(testCaseFile) as fp:
        testCase = json.load(fp)

    fingerprintLength = testCase["settings"]["fingerprint_length"]
    orf = testCase["settings"]["orf"]
    minDuplicateLength = testCase["settings"]["min_duplicate_length"]

    fingerprintBuilder = FingerprintBuilder([fingerprintLength], orf)
    duplicateFinder = DuplicateFinder(fingerprintBuilder)

    duplicatesData = []

    for docData in testCase["docs"]:
        docIdTo = docData["id"]
        docText = docData["text"]
        comparisonTrees = duplicateFinder.buildComparisonTrees(docIdTo, docText)
        duplicatesData += _extractDuplicatesFromTrees(
            comparisonTrees, docIdTo, docText, minDuplicateLength
        )

    pprint(duplicatesData, sort_dicts=False)

    if not testCase.get("failing", False):
        assert duplicatesData == testCase["duplicates"]
