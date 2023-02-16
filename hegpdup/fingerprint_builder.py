from .span import Span

_CHUNKS_TO_IGNORE = {"\n", "\r\n"}


class FingerprintBuilder:
    # thisFolder, fingerprintList, orf

    def __init__(self, fingerprintLengths, orf):
        """Create object Fingerprints which contains all
        docs fingerprints for a patient fingerprint.

        Parameters
        ----------
        fingerprintLengths : [ int]
            list of fingerprint length.
        orf : int
            define the open reading frame length. the size of the shift
            when a text is read.

        Returns
        -------
        type object
            retured Fingerprints object.

        """

        self.fingerprintLengths = fingerprintLengths
        self.orf = orf

        self._fingerprintIdByChunk = dict()

    def buildFingerprints(self, text):
        spansByFingerprintId = {}
        # lowercase so we aren't case sensitive
        text = text.lower()
        # found the right position in text
        lineOffset = 0
        # Cadre de lecture
        # gere le multiline
        for linePosition in range(0, min(self.orf, len(text))):
            # split the text in n slice in chunck
            line = "".join(text[linePosition:])
            # gere cadre de lecture[0 et +1]
            self._buildFingerprintsForLine(line, lineOffset, spansByFingerprintId)
            # Update linePosition value
            lineOffset = lineOffset + len(text[linePosition])

        return spansByFingerprintId

    def _buildFingerprintsForLine(self, line, lineOffset, spansByFingerprintId):
        """For a given line, create the appropriate
        text chunks to generate fingerprint.

        Parameters
        ----------
        line : str
            a doc line.
        lineOffset : int
            real text position.
        """

        # gere cadre de lecture[0 et +1]
        for fingerprintLength in self.fingerprintLengths:
            chunkStarts = range(0, len(line), self.orf)
            for chunkStart in chunkStarts:
                self._buildFingerprintForChunk(
                    chunkStart,
                    line,
                    lineOffset,
                    fingerprintLength,
                    spansByFingerprintId,
                )
                if chunkStart + fingerprintLength >= len(line):
                    break

    def _buildFingerprintForChunk(
        self,
        chunkStart,
        line,
        lineOffset,
        fingerprintLength,
        spansByFingerprintId,
    ):
        """generate fingerprints

        Parameters
        ----------
        chunkStart : int
            a round number which will split text size
            by the lengght of the fingerprint.
        line : str
            current line we are working on.
        lineOffset : int
            real position to evaluate.
        fingerprintLength : int
            fingerprint length to generate.
        """

        chunk = line[chunkStart : chunkStart + fingerprintLength]
        if chunk in _CHUNKS_TO_IGNORE:
            return

        if chunk not in self._fingerprintIdByChunk.keys():
            fingerprintId = len(self._fingerprintIdByChunk) + 1
            self._fingerprintIdByChunk[chunk] = fingerprintId

        start = lineOffset + chunkStart
        # NB chunk might be shorter than fingerprintLength
        end = start + len(chunk)
        otherCandidate = Span(start=start, end=end)

        spansByFingerprintId.setdefault(self._fingerprintIdByChunk[chunk], []).append(
            otherCandidate
        )
