import pytest

from duplicatefinder import WordFingerprintBuilder, Span


@pytest.fixture(scope="module", autouse=True)
def mock_span_eq(module_mocker):
    """Add __eq__ function to Span just for the tests of this file"""

    def spans_are_equal(self, other):
        return self.start == other.start and self.end == other.end

    module_mocker.patch(
        "duplicatefinder.Span.__eq__",
        spans_are_equal,
    )


def test_multiline():
    text = "\n\nHi Bob\nHello Bob\n\n"

    builder = WordFingerprintBuilder(fingerprintLength=100, allowMultiline=True)
    spansAndFingerprints = builder.buildFingerprints(text)
    # 1 fingerprint covering all the lines (except leading/trailing)
    assert spansAndFingerprints == [(Span(2, len(text) - 2), "Hi Bob\nHello Bob")]

    builder = WordFingerprintBuilder(fingerprintLength=100, allowMultiline=False)
    spansAndFingerprints = builder.buildFingerprints(text)
    # 1 fingerprint fingerprint per line, without any newline char
    assert spansAndFingerprints == [
        (Span(2, 8), "Hi Bob"),
        (Span(9, 18), "Hello Bob"),
    ]


def test_fingerprints_boundaries():
    """Test fingerprints are built by concatenating words and in-between chars"""

    builder = WordFingerprintBuilder(fingerprintLength=3)

    # spaces and non-words characters between words are included in chunks
    # leading and trailing non-word chars are not included in any chunk
    text = "- Hello, Alice,   what's up?  "
    spansAndFingerprints = builder.buildFingerprints(text)
    fingerprints = [f for _, f in spansAndFingerprints]
    assert fingerprints == ["Hello, Alice,   what", "Alice,   what's", "what's up"]

    # edge case: number of words less that fingerprint length
    text = " - Hello, Alice "
    spansAndFingerprints = builder.buildFingerprints(text)
    fingerprints = [f for _, f in spansAndFingerprints]
    assert fingerprints == ["Hello, Alice"]


_TEST_CASES = [
    # fingerprintLength=2, orf=1
    (
        2,
        1,
        [
            (Span(0, 10), "hello, how"),
            (Span(7, 14), "how are"),
            (Span(11, 18), "are you"),
            (Span(15, 23), "you? how"),
            (Span(20, 27), "how are"),
            (Span(24, 34), "are things"),
        ],
    ),
    # fingerprintLength=3, orf=1
    (
        3,
        1,
        [
            (Span(0, 14), "hello, how are"),
            (Span(7, 18), "how are you"),
            (Span(11, 23), "are you? how"),
            (Span(15, 27), "you? how are"),
            (Span(20, 34), "how are things"),
        ],
    ),
    # fingerprintLength=2, orf=2
    (
        2,
        2,
        [
            (Span(0, 10), "hello, how"),
            (Span(11, 18), "are you"),
            (Span(20, 27), "how are"),
            (Span(28, 34), "things"),  # tail chunk is shorter but not left out
        ],
    ),
]


@pytest.mark.parametrize(
    "fingerprintLength,orf,expectedspansAndFingerprints", _TEST_CASES
)
def test_fingerprint_length_orf_combinations(
    fingerprintLength, orf, expectedspansAndFingerprints
):
    """
    Test spans and fingerprints obtained for various combinations of
    fingerprint lengths and orfs for a given text
    """

    text = "hello, how are you? how are things?"

    builder = WordFingerprintBuilder(fingerprintLength, orf)
    spansAndFingerprints = builder.buildFingerprints(text)
    assert spansAndFingerprints == expectedspansAndFingerprints
