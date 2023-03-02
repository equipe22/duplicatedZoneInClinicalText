import pytest

from hegpdup import CharFingerprintBuilder, Span


@pytest.fixture(scope="module", autouse=True)
def mock_span_eq(module_mocker):
    """Add __eq__ function to Span just for the tests of this file"""

    def spans_are_equal(self, other):
        return self.start == other.start and self.end == other.end

    module_mocker.patch(
        "hegpdup.Span.__eq__",
        spans_are_equal,
    )


def test_multiline():
    text = "\n\nHi\nHello\n\n"

    builder = CharFingerprintBuilder(fingerprintLength=100, allowMultiline=True)
    spansAndFingerprints = builder.buildFingerprints(text)
    # 1 fingerprint span covering all the lines
    assert spansAndFingerprints == [(Span(0, len(text)), text)]

    builder = CharFingerprintBuilder(fingerprintLength=100, allowMultiline=False)
    spansAndFingerprints = builder.buildFingerprints(text)
    # 1 fingerprint per line, without any newline char
    assert spansAndFingerprints == [
        (Span(2, 4), "Hi"),
        (Span(5, 10), "Hello"),
    ]


_TEST_CASES = [
    # fingerprintLength=1, orf=1
    (
        1,
        1,
        [
            (Span(0, 1), "a"),
            (Span(1, 2), "b"),
            (Span(2, 3), "c"),
            (Span(3, 4), "d"),
            (Span(4, 5), "a"),
            (Span(5, 6), "b"),
            (Span(6, 7), "c"),
        ],
    ),
    # fingerprintLength=2, orf=1
    (
        2,
        1,
        [
            (Span(0, 2), "ab"),
            (Span(1, 3), "bc"),
            (Span(2, 4), "cd"),
            (Span(3, 5), "da"),
            (Span(4, 6), "ab"),
            (Span(5, 7), "bc"),
        ],
    ),
    # fingerprintLength=3, orf=1
    (
        3,
        1,
        [
            (Span(0, 3), "abc"),
            (Span(1, 4), "bcd"),
            (Span(2, 5), "cda"),
            (Span(3, 6), "dab"),
            (Span(4, 7), "abc"),
        ],
    ),
    # fingerprintLength=2, orf=2
    (
        2,
        2,
        [
            (Span(0, 2), "ab"),
            (Span(2, 4), "cd"),
            (Span(4, 6), "ab"),
            (Span(6, 7), "c"),  # tail chunk is shorter but not left out
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

    text = "abcdabc"

    builder = CharFingerprintBuilder(fingerprintLength, orf)
    spansAndFingerprints = builder.buildFingerprints(text)
    assert spansAndFingerprints == expectedspansAndFingerprints
