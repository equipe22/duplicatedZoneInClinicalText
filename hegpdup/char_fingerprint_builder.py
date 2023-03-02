import re
import warnings

from .span import Span

_LINE_REGEXP = re.compile(r"[^\r\n]+")


class CharFingerprintBuilder:
    """
    Build fingerprints for a set of text documents by grouping together
    characters. To be used within a `DuplicateFinder`.

    The goal of fingerprinting is to speed up the look for common sequences of
    consecutive chars between 2 texts. Instead of starting with a char-by-char
    comparison as in classical diff algorithms, we directly start with sequences
    of several chars, which will drastically reduce the number of false
    duplicate candidates later discarded. The trade-off is that we are not able
    to find duplicates shorter than the fingerprint length.

    Each text passed to `buildFingerprints()` is scanned by a window (a bit like
    a convolution) of length `fingerprintLength` (in number of chars) and a
    shift size of `orf` (also in number of chars). At each step, a fingerprint
    is created by taking the text in the window.

    For instance, the text "Alice is nice", fingerprinted with a fingerprint
    length of 3 and an orf of 1, would yield the following fingerprints:
        - "Ali"
        - "lic"
        - "ice"
        - "ce "
        - "e i"
        - " is"
        - "s n"
        - " ni"
        - "nic"
        - "ice"  # identical to 3rd fingerprint
    """

    def __init__(
        self, fingerprintLength, orf=1, caseSensitive=True, allowMultiline=True
    ):
        """
        Parameters
        ----------
        fingerprintLength: int
            Number of characters in fingerprints. The longer, the faster
            `DuplicateFinder` will be. But the longer, the more duplicates will
            be missed.

            In a nutshell, `fingerprintLength` should be right above the
            length of duplicates that we don't mind missing, and the
            `minDuplicateLength` of `DuplicateFinder` should be set to the same
            value.

            When building duplicates between 2 documents, `DuplicateFinder` will
            iterate over all the fingerprints of the 1st document, and for each
            of them, all the identical fingerprints of the 2d document.

            So increasing the fingerprint length has the effect of:
             - decreasing the number of fingerprints, both in the 1st and 2d
               documents. So this should reduce the number of iterations in the
               nested loop quadratically (if I am not mistaken)
             - decreasing the number of common fingerprints because the longer
               is each fingerprint, the less likely it is to have identical
               fingerprints

            But we can't increase the fingerprint length too much because
            `DuplicateFinder` won't be able to find duplicates shorter than the
            fingerprinted length. For instance, fingerprinting these texts:
                "Hi Bob"
            and
                "Hello Bob"
            with an fingerprint length of 4 and and orf of 1 will yield the
            following fingerprints, respectively:
                "Hi B", "i Bo", " Bob"
            and
                "Hell", "ello", "llo ", "lo B", "o Bo", " Bob"
            and there are no common fingerprints between the 2 texts so no
            duplicate will be detected.

            So `fingerprintLength` should be set to the same value as
            `minDuplicateLength`.
        orf: int
            Open Reading Frame, ie the shift size (in number of chars) used when
            moving the fingerprint window over the text. If not missing any
            duplicates is important, then this should be set to 1, because
            otherwise potential duplicates (even very long) can be missed if
            they were fingerprinted with a different offset.

            For instance, fingerprinting these texts:
                "Hello Alice"
            and
                "Hi Alice"
            with an fingerprint length of 4 and an orf of 2 will yield the
            following fingerprints, respectively:
                "Hell", "llo ", "o Al", "Alic", "ice"
            and
                "Hi A", " Ali", "lice"
            and there are no common fingerprints between the 2 texts so no
            duplicate will be detected.
        caseSensitive: bool
            If False, all fingerprints will be converted to lowercase, thus
            making duplicate detection case-insensitive
        allowMultiline: bool
            Whether fingerprints can span over multiple lines. Set to False
            to prevent multiline duplicates
        """

        if fingerprintLength < 1:
            raise ValueError("Fingerprint length must be at least 1")
        elif fingerprintLength < 2:
            warnings.warn(
                "Using a fingerprint of smaller than 2 defeats the purpose of fingerprinting "
                "since there will be one fingerprint per character. Duplicate finding is going "
                "to be very slow."
            )
        if orf < 1:
            raise ValueError("ORF must be at least 1")
        elif orf > 1:
            warnings.warn(
                "Using and ORF bigger than 1 will probably lead to many duplicates being missed"
            )

        self.fingerprintLength = fingerprintLength
        self.orf = orf
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
            List of fingerprints contained in `text` and their
            corresponding characters spans, sorted by ascending span
        """

        if not self.caseSensitive:
            text = text.lower()

        if self.allowMultiline:
            return list(self._buildFingerprints(text, 0))

        # build fingerprints line by line if multiline fingerprints aren't
        # allowed
        spansAndFingerprints = []
        for match in _LINE_REGEXP.finditer(text):
            lineStart = match.start()
            line = match.group()
            spansAndFingerprintsForLine = self._buildFingerprints(line, lineStart)
            spansAndFingerprints.extend(spansAndFingerprintsForLine)

        return spansAndFingerprints

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

        textLength = len(text)
        for start in range(0, textLength, self.orf):
            end = min(start + self.fingerprintLength, textLength)
            fingerprint = text[start:end]
            span = Span(textStart + start, textStart + end)
            yield span, fingerprint

            # if we reached end of text, break out
            if end == textLength:
                break
