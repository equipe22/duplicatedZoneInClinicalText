from pathlib import Path
import timeit

import pytest

from hegpdup.fingerprint_builder import FingerprintBuilder
from hegpdup.duplicate_finder import DuplicateFinder, TreeBackend

_TEXT_FILE = Path(__file__).parent / "sample_text.txt"
_FINGERPRINT_LENGTH = 10
_ORF = 3
_MIN_DUPLICATE_LENGTH = 10


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

    time = timeit.timeit(run, number=10)
    print(treeBackend.value, time)


if __name__ == "__main__":
    # launch with python3 -O tests/test_speed.py for best results
    for treeBackend in TreeBackend:
        test_speed(treeBackend)
