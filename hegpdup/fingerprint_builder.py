from .span import Span

_CHUNKS_TO_IGNORE = {"\n", "\r\n"}


class FingerprintBuilder:
    """
    Builds fingerprints for a set of text documents, for identification of
    duplicates.

    The `FingerprintBuilder` remembers previously seen documents and will reuse
    fingerprint ids for identical text chunks.
    """

    def __init__(self, fingerprintLengths, orf):
        """
        Parameters
        ----------
        fingerprintLengths: List[int]
            Lengths to use for generated fingerprints (provide at least one)
        orf: int
            Open Reading Frame length. Shift size used when moving the
            fingerprint window over the text (the window having a size)
        """

        self.fingerprintLengths = fingerprintLengths
        self.orf = orf

        # mapping giving the unique fingerprint id corresponding to a previously
        # seen chunk of text
        self._fingerprintIdByChunk = dict()

    def buildFingerprints(self, text):
        """
        Return a mapping of fingerprint ids and the character spans in which
        they are found in `text`

        Parameters
        ----------
        text: str
            Text for which to build the fingerprints

        Returns
        -------
        Dict[int, List[Span]]
            Ids of fingerprints contained in `text` and their corresponding
            characters spans
        """

        # mapping that will be filled and returned
        spansByFingerprintId = {}

        # lowercase so we aren't case sensitive
        text = text.lower()

        # position of the 1st char of the current line
        lineOffset = 0
        for linePosition in range(0, min(self.orf, len(text))):
            # not sure what that does, something to do with multiline?
            line = "".join(text[linePosition:])
            # build fingerprints for current line and add them to spansByFingerprintId
            self._buildFingerprintsForLine(line, lineOffset, spansByFingerprintId)

            lineOffset = lineOffset + len(text[linePosition])

        return spansByFingerprintId

    def _buildFingerprintsForLine(self, line, lineOffset, spansByFingerprintId):
        """
        Build the fingerprints of a line and add them to `spansByFingerprintId`

        Parameters
        ----------
        line: str
            Line for which to build the fingerprints
        lineOffset: int
            Position of the line in the full document text
        spansByFingerprintId: Dict[int, List[Span]]
            Mapping to which the fingerprint ids and corresponding spans will
            be added
        """

        lineLength = len(line)
        for fingerprintLength in self.fingerprintLengths:
            # construct all chunk offsets in line
            # (fingerprints will overlap)
            chunkStarts = range(0, len(line), self.orf)
            for chunkStart in chunkStarts:
                chunkEnd = chunkStart + fingerprintLength
                chunk = line[chunkStart:chunkEnd]

                if chunk in _CHUNKS_TO_IGNORE:
                    return

                # find existing fingerprint id for chunk or create new id
                # if chunk is unseen
                fingerprintId = self._fingerprintIdByChunk.setdefault(
                    chunk, len(self._fingerprintIdByChunk)
                )

                # create and store span
                start = lineOffset + chunkStart
                # chunk might end up being shorter than fingerprintLength
                end = start + len(chunk)
                span = Span(start, end)
                spansByFingerprintId.setdefault(fingerprintId, []).append(span)
                if chunkEnd >= lineLength:
                    break
