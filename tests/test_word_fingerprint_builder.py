import pytest

from hegpdup import WordFingerprintBuilder, Span


@pytest.fixture(scope="module", autouse=True)
def mock_span_eq(module_mocker):
    """Add __eq__ function to Span just for the tests of this file"""

    def spans_are_equal(self, other):
        return self.start == other.start and self.end == other.end

    module_mocker.patch(
        "hegpdup.Span.__eq__",
        spans_are_equal,
    )


def _spansAndFingerprintIdsToChunkTexts(spansAndFingerprintIds, text):
    return [text[s.start : s.end] for s, _ in spansAndFingerprintIds]


def test_multiline():
    text = "\n\nHi Bob\nHello Bob\n\n"

    builder = WordFingerprintBuilder(fingerprintLength=100, allowMultiline=True)
    spansAndFingerprintIds = builder.buildFingerprints(text)
    # 1 fingerprinted span covering all the lines (except leading/trailing)
    assert len(spansAndFingerprintIds) == 1
    span, _ = spansAndFingerprintIds[0]
    assert span == Span(2, len(text) - 2)

    builder = WordFingerprintBuilder(fingerprintLength=100, allowMultiline=False)
    spansAndFingerprintIds = builder.buildFingerprints(text)
    # 1 fingerprinted span fingerprint per line, without any newline char
    assert len(spansAndFingerprintIds) == 2
    span1, _ = spansAndFingerprintIds[0]
    assert span1 == Span(2, 8)  # Hi Bob
    span2, _ = spansAndFingerprintIds[1]
    assert span2 == Span(9, 18)  # Hello Bob


def test_chunks():
    """Test chunks are built by concatenating words and in-between chars"""

    builder = WordFingerprintBuilder(fingerprintLength=3)

    # spaces and non-words characters between words are included in chunks
    # leading and trailing non-word chars are not included in any chunk
    text = "- Hello, Alice,   what's up?  "
    spansAndFingerprintIds = builder.buildFingerprints(text)
    chunkTexts = _spansAndFingerprintIdsToChunkTexts(spansAndFingerprintIds, text)
    assert chunkTexts == ["Hello, Alice,   what", "Alice,   what's", "what's up"]

    # edge case: number of words less that fingerprint length
    text = " - Hello, Alice "
    spansAndFingerprintIds = builder.buildFingerprints(text)
    chunkTexts = _spansAndFingerprintIdsToChunkTexts(spansAndFingerprintIds, text)
    assert chunkTexts == ["Hello, Alice"]


_TEST_CASES = [
    # fingerprintLength=2, orf=1
    (
        2,
        1,
        [
            (Span(0, 10), 0),  # hello, how
            (Span(7, 14), 1),  # how are
            (Span(11, 18), 2),  # are you
            (Span(15, 23), 3),  # you? how
            (Span(20, 27), 1),  # how are
            (Span(24, 34), 4),  # are things
        ],
    ),
    # fingerprintLength=3, orf=1
    (
        3,
        1,
        [
            (Span(0, 14), 0),  # hello, how are
            (Span(7, 18), 1),  # how are you
            (Span(11, 23), 2),  # are you? how
            (Span(15, 27), 3),  # you? how are
            (Span(20, 34), 4),  # how are things
        ],
    ),
    # fingerprintLength=2, orf=2
    (
        2,
        2,
        [
            (Span(0, 10), 0),  # hello, how
            (Span(11, 18), 1),  # are you
            (Span(20, 27), 2),  # how are
            (Span(28, 34), 3),  # things (tail chunk is shorter but not left out)
        ],
    ),
]


@pytest.mark.parametrize(
    "fingerprintLength,orf,expectedSpansAndFingerprintIds", _TEST_CASES
)
def test_fingerprint_length_orf_combinations(
    fingerprintLength, orf, expectedSpansAndFingerprintIds
):
    """
    Test spans and fingerprint ids obtained for various combinations of
    fingerprint lengths and orfs for a given text
    """
    text = "hello, how are you? how are things?"

    builder = WordFingerprintBuilder(fingerprintLength, orf)
    spansAndFingerprintIds = builder.buildFingerprints(text)
    assert spansAndFingerprintIds == expectedSpansAndFingerprintIds
