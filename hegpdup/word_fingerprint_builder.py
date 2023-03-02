import re
import warnings

from .span import Span

_DEFAULT_WORD_REGEXP = re.compile(r"[\w\d]+")
_LINE_REGEXP = re.compile(r"[^\r\n]+")


class WordFingerprintBuilder:
    """
    Build fingerprints for a set of text documents by grouping together
    characters. To be used within a `DuplicateFinder`.

    The goal of fingerprinting is to speed up the look for common sequences of
    consecutive chars between 2 texts. Instead of starting with a char-by-char
    comparison as in classical diff algorithms, we directly start with sequences
    of several chars, which will drastically reduce the number of false
    duplicate candidates later discarded. The trade-off is that we are not able
    to find duplicates shorter than the fingerprint length.

    Each text passed to `buildFingerprints()` is split into a sequence of words.
    Then this sequence scanned by a window (a bit like a convolution) of length
    `fingerprintLength` (in number of words) and a shift size of `orf` (also in
    number of words).

    At each step, a fingerprint is created by taking the text starting from the
    1st word in the window to the last one (including in-between non-words
    characters).

    For instance, the text "How are you? How are things?", fingerprinted with a
    fingerprint length of 2 and an orf of 1, would yield the following
    fingerprints:
        - "How are"
        - "are you"
        - "you? How"
        - "How are"  # identical to 1st fingerprint
        - "are things"

    Notice how the trailing question mark was not included in any fingerprint,
    as it is not located between any words. Indeed, compared to
    `CharFingerprintBuilder`, `WordFingerprintBuilder` assumes we are only
    interested in detecting the duplication of words.

    The main advantage of this assumption is that it allows a performance gain
    because we will have less fingerprints, not because the fingerprints are
    bigger (they are not necessarily, compared to using a
    `CharFingerprintBuilder` with a fingerprint length close to the average word
    length), but because with an orf of 1 we are stepping over 1 word, ie
    several chars, instead of 1 char.

    To illustrate this, let's take a text composed of only 3-chars words:
        "Yes she can"
    and fingerprint it with a `CharFingerprintBuilder` with a fingerprint length
    of 6 and an orf of 1, which would yield the following fingerprints:
        "Yes sh", "es she", "s she ", " she c", "she ca", "he can"
    while a `WordFingerprintBuilder` with fingerprint length of 2 and orf of 1
    will yield:
        "Yes she", "she can"
    We have the same text coverage with identical fingerprint lengths, but less
    fingerprints, which will speed up the comparison (cf docstring of
    `CharFingerprintBuilder` for an explanation of why is it better to have less
    fingerprints).

    The only thing we lose is the ability to detect "sub-word" duplications,
    which might actually be a good thing. Another limit compared to
    `CharFingerprintBuilder` is that is is not possible to have a fingerprint
    length of 1 (it must be at least 2), because otherwise the characters
    between words wouldn't be fingerprinted at all. The fingerprints wouldn't be
    adjacent, there would be gaps and because of the gaps we wouldn't be able to
    find duplicates going across several words.
    """

    def __init__(
        self,
        fingerprintLength=2,
        orf=1,
        wordRegexp=_DEFAULT_WORD_REGEXP,
        caseSensitive=True,
        allowMultiline=True,
    ):
        """
        Parameters
        ----------
        fingerprintLength: int
            Number of words in fingerprints. The non-words characters between
            the words of a fingerprint will also be included in the
            fingerprints. Must be at least 2 otherwise there would be gaps
            between all fingerprints.

            The longer, the faster `DuplicateFinder` will be, cf docstring of
            `CharFingerprintBuilder` for an explanation.

            `fingerprintLength` should be right above the length (in words) of
            duplicates that we don't mind missing. The `minDuplicateLength` of
            `DuplicateFinder` should be set in consistency of the fingerprint
            length, for instance to the `fingerprintLength` multiplied by the
            average number of chars in a word.
        orf: int
            Open Reading Frame, ie the shift size (in number of words) used when
            moving the fingerprint window over the text. If not missing any
            duplicates is important, then this should be set to 1, because
            otherwise potential duplicates (even very long) can be missed if
            they were fingerprinted with a different offset, cf docstring
            `CharFingerprintBuilder` for an explanation.
        wordRegexp: re.Pattern
            Regexp object to use to identify word boundaries in texts
        caseSensitive: bool
            If False, all fingerprints will be converted to lowercase, thus
            making duplicate detection case-insensitive
        allowMultiline: bool
            Whether fingerprints can span over multiple lines. Set to False
            to prevent multiline duplicates
        """

        if fingerprintLength < 2:
            raise ValueError("Fingerprint length must be at least 2")
        if orf < 1:
            raise ValueError("ORF must be at least 1")
        elif orf > 1:
            warnings.warn(
                "Using and ORF bigger than 1 will probably lead to many duplicates being missed"
            )

        self.fingerprintLength = fingerprintLength
        self.orf = orf
        self.wordRegexp = wordRegexp
        self.caseSensitive = caseSensitive
        self.allowMultiline = allowMultiline

    def buildFingerprints(self, text):
        """
        Return a list of fingerprints and the character spans in which
        they are found in `text`.

        Parameters
        ----------
        text: str
            Text for which to build the fingerprints

        Returns
        -------
        List[Tuple[Span, str]]
            List of fingerprints contained in `text` and their corresponding
            characters spans, sorted by ascending span
        """

        if not self.caseSensitive:
            text = text.lower()

        if self.allowMultiline:
            return list(self._buildFingerprints(text, 0))

        # build fingerprints line by line if multiline fingerprints aren't
        # allowed
        spansAndFingerprintIds = []
        for match in _LINE_REGEXP.finditer(text):
            lineStart = match.start()
            line = match.group()
            spansAndFingerprintIdsForLine = self._buildFingerprints(line, lineStart)
            spansAndFingerprintIds.extend(spansAndFingerprintIdsForLine)

        return spansAndFingerprintIds

    def _buildFingerprints(self, text, textStart=0):
        """
        Yield fingerprints and character spans in which they are found in
        `text`, using `textStart` to offset the spans.

        Parameters
        ----------
        text: str
            Text for which to build the fingerprints
        textStart:
            Position of `text` in the full document text if it is a line rather
            than the full text

        Returns
        -------
        Iterator[Tuple[Span, str]]
            Iterator over fingerprints contained in `text` and their
            corresponding characters spans, sorted by ascending span
        """

        # get start/end boundaries of all words using regexp
        wordSpans = [match.span() for match in self.wordRegexp.finditer(text)]

        # build fingerprints for consecutive words
        nbWords = len(wordSpans)
        for i in range(0, nbWords, self.orf):
            # take start of current word
            start, _ = wordSpans[i]
            # take end of last word to include in fingerprint
            end_i = min(i + self.fingerprintLength, nbWords)
            _, end = wordSpans[end_i - 1]

            fingerprint = text[start:end]
            span = Span(textStart + start, textStart + end)
            yield span, fingerprint

            # if we reached end of list of words, break out
            if end_i == nbWords:
                break
