from pathlib import Path
import timeit

from hegpdup.fingerprints import Fingerprints
from hegpdup.doctrees import DocTrees

_TEXT_FILE = Path(__file__).parent / "sample_text.txt"
_FINGERPRINT_LENGTH = 10
_ORF = 3


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


def test_speed():
    texts = _getSampleTexts()

    def run():
        fingerprints = Fingerprints([_FINGERPRINT_LENGTH], _ORF, texts)
        doctrees = DocTrees()
        doctrees.buildTree_comparisons(fingerprints.figprintId)
        doctrees.mergeOverlap(fingerprints.figprintId)
        doctrees.expandOverlap()

    time = timeit.timeit(run, number=10)
    print(time)


if __name__ == "__main__":
    # launch with python3 -O tests/test_speed.py for best results
    test_speed()
