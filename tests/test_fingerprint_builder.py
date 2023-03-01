import pytest

from hegpdup import FingerprintBuilder, Span


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

    builder = FingerprintBuilder(fingerprintLength=100, allowMultiline=True)
    spansAndFingerprintIds = builder.buildFingerprints(text)
    # 1 fingerprinted span covering all the lines
    assert len(spansAndFingerprintIds) == 1
    span, _ = spansAndFingerprintIds[0]
    assert span == Span(0, len(text))

    builder = FingerprintBuilder(fingerprintLength=100, allowMultiline=False)
    spansAndFingerprintIds = builder.buildFingerprints(text)
    # 1 fingerprinted span fingerprint per line, without any newline char
    assert len(spansAndFingerprintIds) == 2
    span1, _ = spansAndFingerprintIds[0]
    assert span1 == Span(2, 4)  # Hi
    span2, _ = spansAndFingerprintIds[1]
    assert span2 == Span(5, 10)  # Hello


_TEST_CASES = [
    # fingerprintLength=1, orf=1
    (
        1,
        1,
        [
            (Span(0, 1), 0),  # a
            (Span(1, 2), 1),  # b
            (Span(2, 3), 2),  # c
            (Span(3, 4), 3),  # d
            (Span(4, 5), 0),  # a
            (Span(5, 6), 1),  # b
            (Span(6, 7), 2),  # c
        ],
    ),
    # fingerprintLength=2, orf=1
    (
        2,
        1,
        [
            (Span(0, 2), 0),  # ab
            (Span(1, 3), 1),  # bc
            (Span(2, 4), 2),  # cd
            (Span(3, 5), 3),  # da
            (Span(4, 6), 0),  # ab
            (Span(5, 7), 1),  # bc
        ],
    ),
    # fingerprintLength=3, orf=1
    (
        3,
        1,
        [
            (Span(0, 3), 0),  # abc
            (Span(1, 4), 1),  # bcd
            (Span(2, 5), 2),  # cda
            (Span(3, 6), 3),  # dab
            (Span(4, 7), 0),  # abc
        ],
    ),
    # fingerprintLength=2, orf=2
    (
        2,
        2,
        [
            (Span(0, 2), 0),  # ab
            (Span(2, 4), 1),  # cd
            (Span(4, 6), 0),  # ab
            (Span(6, 7), 2),  # c (tail chunk is shorter but not left out)
        ],
    ),
]


@pytest.mark.parametrize(
    "fingerprintLength,orf,expectedSpansAndFingerprintIds", _TEST_CASES
)
def test_fingerprint_length_orf_combinations(
    fingerprintLength, orf, expectedSpansAndFingerprintIds
):
    text = "abcdabc"

    builder = FingerprintBuilder(fingerprintLength, orf)
    spansAndFingerprintIds = builder.buildFingerprints(text)
    assert spansAndFingerprintIds == expectedSpansAndFingerprintIds
