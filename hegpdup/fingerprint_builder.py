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

        lineLength = len(line)
        # gere cadre de lecture[0 et +1]
        for fingerprintLength in self.fingerprintLengths:
            chunkStarts = range(0, len(line), self.orf)
            for chunkStart in chunkStarts:
                chunkEnd = chunkStart + fingerprintLength
                chunk = line[chunkStart:chunkEnd]

                if chunk in _CHUNKS_TO_IGNORE:
                    return

                fingerprintId = self._fingerprintIdByChunk.setdefault(
                    chunk, len(self._fingerprintIdByChunk)
                )

                start = lineOffset + chunkStart
                # chunk might end up being shorter than fingerprintLength
                end = start + len(chunk)
                span = Span(start, end)
                spansByFingerprintId.setdefault(fingerprintId, []).append(span)
                if chunkEnd >= lineLength:
                    break
