import re

from .span import Span

_NEWLINE_REGEXP = re.compile(r"[^\r\n]+")


class CharFingerprintBuilder:
    """
    Builds fingerprints for a set of text documents by grouping together
    characters.

    The fingerprint builder remembers previously seen documents and will reuse
    fingerprint ids for identical text chunks.
    """

    def __init__(
        self, fingerprintLength, orf=1, caseSensitive=True, allowMultiline=True
    ):
        """
        Parameters
        ----------
        fingerprintLength: int
            Length to use for generated fingerprints
        orf: int
            Open Reading Frame length. Shift size used when moving the
            fingerprint window over the text (the window having a size of
            `fingerprintLength` chars)
        caseSensitive: bool
            Whether case should be taken into account when testing if chunks of
            text are equal
        allowMultiline: bool
            Whether fingerprints can span over multiple lines. Set to False
            to prevent multiline duplicates
        """

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
        for match in _NEWLINE_REGEXP.finditer(text):
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
