import re
import warnings

from .span import Span

_LINE_REGEXP = re.compile(r"[^\r\n]+")


class CharFingerprintBuilder:
    """
    Builds fingerprints for a set of text documents by grouping together
    characters. To be used within a `DuplicateFinder`.

    Each text passed to `buildFingerprints()` is scanned by a window (a bit like
    a convolution) of length `fingerprintLength` (in number of chars) and a
    shift size of `orf` (also in number of chars).

    At each step, a fingerprint id is generated for the chunk of text in the
    window. Either an identical chunk of text has already been encountered, then
    the unique fingerprint id associated to that chunk is used, or the chunk of
    text has never been seen and a new fingerprint id is generated (and stored).

    For instance, the text "Alice is nice", fingerprinted with a fingerprint
    length of 3 and an orf of 1, would yield the following chunks and
    fingerprint ids:
        - "Ali", id=0
        - "lic", id=1
        - "ice", id=2
        - "ce ", id=3
        - "e i", id=4
        - " is", id=5
        - "s n", id=6
        - " ni", id=7
        - "nic", id=8
        - "ice", id=2  # chunk already seen, same fingerprint id

    `CharFingerprintBuilder` remembers previously seen chunks, and will reuse
    fingerprint ids for identical chunks in upcoming calls to
    `buildFingerprints()`. The whole purpose of using fingerprints is that it
    allows us to be faster than a classical char-by-char diff algorithm, because
    we are comparing documents on bigger pieces (chunks) than characters.
    """

    def __init__(
        self, fingerprintLength, orf=1, caseSensitive=True, allowMultiline=True
    ):
        """
        Parameters
        ----------
        fingerprintLength: int
            Number of characters in fingerprinted chunks of text. The longer,
            the faster will `DuplicateFinder` be. But the longer, the more
            duplicate will be missed.

            In a nutshell, `fingerprintLength` should be right above the
            length of duplicates that we don't mind missing, and the
            `minDuplicateLength` of `DuplicateFinder` should be set to the same
            value.

            When building duplicates between 2 documents, `DuplicateFinder` will
            iterate over all the fingerprinted chunks of the 1st document, and
            for each of them, all the fingerprinted chunks of the 2d document
            with the same fingerprint id.

            So increasing the fingerprint length has the effect of:
             - decreasing the number of fingerprinted chunks, both in the 1st
               and 2d documents. So this should reduce the number of iterations
               in the nested loop quadratically (if I am not mistaken)
             - decreasing the number of common fingerprints because the longer
               is each chunk, the less likely it is to have identical chunks

            But we can't increase the fingerprint length too much because
            `DuplicateFinder` won't be able to find duplicates shorter than the
            fingerprinted length. For instance, fingerprinting these texts:
                "Hi Bob"
            and
                "Hello Bob"
            with an fingerprint length of 4 and and orf of 1 will yield
            fingerprint ids for the following chunks respectively:
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
            with an fingerprint length of 4 and and orf of 2 will yield
            fingerprint ids for the following chunks respectively:
                "Hell", "llo ", "o Al", "Alic", "ice"
            and
                "Hi A", " Ali", "lice"
            and there are no common fingerprints between the 2 texts so no
            duplicate will be detected.
        caseSensitive: bool
            Whether case should be taken into account when testing if chunks of
            text are equal
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

        # mapping giving the unique fingerprint id corresponding to a previously
        # seen chunk of text
        self._fingerprintIdByChunk = dict()

    def buildFingerprints(self, text):
        """
        Return a list of fingerprint ids and the character spans in which
        they are found in `text`.

        Parameters
        ----------
        text: str
            Text for which to build the fingerprints

        Returns
        -------
        List[Tuple[Span, int]]
            List of ids of fingerprints contained in `text` and their
            corresponding characters spans, sorted by ascending span
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
        Yield fingerprint ids and character spans in which they are found in
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
        Iterator[Tuple[Span, int]]
            Iterator over ids of fingerprints contained in `text` and their
            corresponding characters spans, sorted by ascending span
        """

        textLength = len(text)
        for start in range(0, textLength, self.orf):
            end = min(start + self.fingerprintLength, textLength)
            chunk = text[start:end]

            # find existing fingerprint id for chunk or create new id
            # if chunk is unseen
            fingerprintId = self._fingerprintIdByChunk.setdefault(
                chunk, len(self._fingerprintIdByChunk)
            )

            span = Span(textStart + start, textStart + end)
            yield span, fingerprintId

            # if we reached end of text, break out
            if end == textLength:
                break
