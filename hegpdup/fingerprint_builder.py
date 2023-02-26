from .span import Span

_CHUNKS_TO_IGNORE = {"\n", "\r\n"}


class FingerprintBuilder:
    """
    Builds fingerprints for a set of text documents, for identification of
    duplicates.

    The `FingerprintBuilder` remembers previously seen documents and will reuse
    fingerprint ids for identical text chunks.
    """

    def __init__(self, fingerprintLength, orf):
        """
        Parameters
        ----------
        fingerprintLength: int
            Length to use for generated fingerprints
        orf: int
            Open Reading Frame length. Shift size used when moving the
            fingerprint window over the text (the window having a size)
        """

        self.fingerprintLength = fingerprintLength
        self.orf = orf

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

        # list that will be filled and returned
        spansAndFingerprintIds = []

        # lowercase so we aren't case sensitive
        text = text.lower()

        # position of the 1st char of the current line
        lineOffset = 0
        for linePosition in range(0, min(self.orf, len(text))):
            # not sure what that does, something to do with multiline?
            line = "".join(text[linePosition:])
            # build fingerprints for current line and add them to spansByFingerprintId
            self._buildFingerprintsForLine(line, lineOffset, spansAndFingerprintIds)

            lineOffset = lineOffset + len(text[linePosition])

        # sort by span
        spansAndFingerprintIds = sorted(
            spansAndFingerprintIds, key=lambda t: (t[0].start, t[0].end)
        )

        return spansAndFingerprintIds

    def _buildFingerprintsForLine(self, line, lineOffset, spansAndFingerprintIds):
        """
        Build the fingerprints of a line and add them to `spansAndFingerprintIds`

        Parameters
        ----------
        line: str
            Line for which to build the fingerprints
        lineOffset: int
            Position of the line in the full document text
        spansAndFingerprintIds: List[Tuple[Span, int]]
            List to which the fingerprint ids and corresponding spans will
            be added
        """

        lineLength = len(line)

        # construct all chunk offsets in line
        # (fingerprints will overlap)
        chunkStarts = range(0, lineLength, self.orf)
        for chunkStart in chunkStarts:
            chunkEnd = chunkStart + self.fingerprintLength
            chunk = line[chunkStart:chunkEnd]
            if chunk in _CHUNKS_TO_IGNORE:
                continue

            # find existing fingerprint id for chunk or create new id
            # if chunk is unseen
            fingerprintId = self._fingerprintIdByChunk.setdefault(
                chunk, len(self._fingerprintIdByChunk)
            )

            # create and store span
            start = lineOffset + chunkStart
            # chunk might end up being shorter than fingerprintLength
            chunkLength = len(chunk)
            end = start + chunkLength
            span = Span(start, end, length=chunkLength)
            spansAndFingerprintIds.append((span, fingerprintId))

            if chunkEnd >= lineLength:
                break
