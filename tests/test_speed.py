import difflib
import itertools
from pathlib import Path
import timeit

import pytest

from hegpdup import FingerprintBuilder, DuplicateFinder, TreeBackend

_TEXT_FILE = Path(__file__).parent / "sample_text.txt"
_FINGERPRINT_LENGTH = 10
_ORF = 3
_MIN_DUPLICATE_LENGTH = 10
_NB_REPEATS = 10


def _getSampleTexts():
    fullText = _TEXT_FILE.read_text()

    text1 = fullText[0:500] + fullText[1500:3000] + fullText[4000:4500]
    text2 = (
        text1[0:500]
        + fullText[5000:6000]
        + text1[500:600]
        + fullText[6000:7000]
        + text1[900:1600]
    )
    text3 = (
        text1[3000:3500]
        + fullText[6000:7000]
        + text2[250:350]
        + fullText[5000:7000]
        + text1[900:1600]
        + text1[600:800]
    )
    text4 = fullText[7000:9000]

    texts = [text1, text2, text3, text4]
    return texts


@pytest.mark.parametrize("treeBackend", TreeBackend)
def test_speed(treeBackend):
    texts = _getSampleTexts()

    def run():
        fingerprintBuilder = FingerprintBuilder([_FINGERPRINT_LENGTH], _ORF)
        duplicateFinder = DuplicateFinder(
            fingerprintBuilder,
            minDuplicateLength=_MIN_DUPLICATE_LENGTH,
            treeBackend=treeBackend,
        )
        for i, text in enumerate(texts):
            duplicateFinder.findDuplicates(f"D{i}", text)

    time = timeit.timeit(run, number=_NB_REPEATS)
    print(treeBackend.value, time)


@pytest.mark.parametrize("treeBackend", TreeBackend)
def test_faster_than_difflib(treeBackend):
    """
    Make sure we are at least 10 times faster than difflib
    """
    texts = _getSampleTexts()

    def run():
        fingerprintBuilder = FingerprintBuilder([_FINGERPRINT_LENGTH], _ORF)
        duplicateFinder = DuplicateFinder(
            fingerprintBuilder,
            minDuplicateLength=_MIN_DUPLICATE_LENGTH,
            treeBackend=treeBackend,
        )
        for i, text in enumerate(texts):
            duplicateFinder.findDuplicates(f"D{i}", text)

    def run_difflib():
        for source_text, target_text in itertools.combinations(texts, 2):
            matcher = difflib.SequenceMatcher(
                a=source_text, b=target_text, autojunk=False
            )
            matcher.get_matching_blocks()

    time = timeit.timeit(run, number=_NB_REPEATS)
    time_difflib = timeit.timeit(run_difflib, number=_NB_REPEATS)
    print(time, time_difflib)

    assert time < (time_difflib / 10)


if __name__ == "__main__":
    # launch with python3 -O tests/test_speed.py for best results
    for treeBackend in TreeBackend:
        test_speed(treeBackend)
        test_faster_than_difflib(treeBackend)
