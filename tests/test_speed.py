import difflib
import itertools
from pathlib import Path
import timeit

import pytest

from hegpdup import FingerprintBuilder, DuplicateFinder, TreeBackend

_SAMPLE_TEXTS_DIR = Path(__file__).parent / "samples"
_FINGERPRINT_LENGTH = 30
_ORF = 15
_MIN_DUPLICATE_LENGTH = 30
_NB_REPEATS = 10


def _getSampleTexts():
    texts = [f.read_text() for f in sorted(_SAMPLE_TEXTS_DIR.glob("*.txt"))]
    # copy/pastes lines across docs
    texts = [t.split("\n") for t in texts]
    # doc 0 is the oldest doc, has no copy/pastes
    # doc 1 has copy/pastes from doc 0
    texts[1][0:5] = texts[0][0:5]
    texts[1][100:110] = texts[0][50:60]
    texts[1][120:125] = texts[0][80:85]
    texts[1][150:155] = texts[0][60:65]
    texts[1][180:185] = texts[0][50:55]
    # doc 2 has copy/pastes from doc 0, and doc 1,
    # including parts of doc 1 that were copy/pasted from doc 0
    texts[2][5:10] = texts[0][20:25]
    texts[2][20:30] = texts[1][115:125]
    texts[2][40:45] = texts[1][20:25]
    texts[2][90:95] = texts[1][30:35]

    texts = ["\n".join(t) for t in texts]
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
