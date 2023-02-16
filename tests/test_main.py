import json
from pathlib import Path
from pprint import pprint

import pytest

from hegpdup.fingerprint_builder import FingerprintBuilder
from hegpdup.duplicate_finder import DuplicateFinder

_TEST_CASES_DIR = Path(__file__).parent / "test_cases"
_TEST_CASES_FILES = sorted(_TEST_CASES_DIR.glob("*.json"))


def _extractDuplicatesFromTrees(trees, minDuplicateLength, docTextsById):
    duplicatesData = []
    for (docIdFrom, docIdTo), tree in trees.items():
        seen = set()
        for interval in sorted(tree):
            if (interval.end - interval.begin) < minDuplicateLength:
                continue
            if (interval.begin, interval.end) in seen:
                continue

            targetStart = interval.data.start
            targetEnd = interval.data.end
            text = docTextsById[docIdTo][targetStart:targetEnd]

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
    docTexts = [doc["text"] for doc in testCase["docs"]]

    fingerprintBuilder = FingerprintBuilder([fingerprintLength], orf, docTexts)

    duplicateFinder = DuplicateFinder()
    duplicateFinder.buildTree_comparisons(fingerprintBuilder.figprintId)

    docTextsById = {docData["id"]: docData["text"] for docData in testCase["docs"]}
    duplicatesData = _extractDuplicatesFromTrees(
        duplicateFinder.resultTree, minDuplicateLength, docTextsById
    )

    pprint(duplicatesData, sort_dicts=False)

    if not testCase.get("failing", False):
        assert duplicatesData == testCase["duplicates"]
