class FingerprintLocation:
    __slots__ = "name", "start", "end"

    def __init__(self, name, start, end):
        self.name = name
        self.start = start
        self.end = end

    def __hash__(self):
        return hash((self.name, self.start, self.end))

    def __repr__(self):
        return (
            f"FingerprintLocation(name={self.name}, start={self.start}, end={self.end})"
        )


_CHUNKS_TO_IGNORE = {"\n", "\r\n"}


class FingerprintBuilder:
    # thisFolder, fingerprintList, orf

    def __init__(self, fingerprintList, orf):
        """Create object Fingerprints which contains all
        docs fingerprints for a patient fingerprint.

        Parameters
        ----------
        fingerprintList : [ int]
            list of fingerprint length.
        orf : int
            define the open reading frame length. the size of the shift
            when a text is read.

        Returns
        -------
        type object
            retured Fingerprints object.

        """

        self.fingerprintList = fingerprintList
        self.orf = orf
        # contains list of fingerprint
        self.figprint = dict()

    def generateFingerprints(self, name, data):
        figprintId = {}
        # lowercase so we aren't case sensitive
        data = data.lower()
        # found the right position in text
        realposition = 0
        # Cadre de lecture
        # gere le multiline
        for linePosition in range(0, min(self.orf, len(data))):
            # split the text in n slice in chunck
            line = "".join(data[linePosition:])
            # gere cadre de lecture[0 et +1]
            self.createChunks(line, realposition, name, figprintId)
            # Update linePosition value
            realposition = realposition + len(data[linePosition])

        return figprintId

    def createChunks(self, line, realposition, thisfile, figprintId):
        """For a given line, create the appropriate
        text chunks to generate fingerprint.

        Parameters
        ----------
        line : str
            a doc line.
        realposition : int
            real text position.
        thisfile :tuple
            contains path to the file to work on.
        """

        # gere cadre de lecture[0 et +1]
        for fingerprintLen in self.fingerprintList:
            listCadreLecture = range(0, len(line), self.orf)
            for i in listCadreLecture:
                self.treatChunk(
                    i,
                    thisfile,
                    line,
                    realposition,
                    fingerprintLen,
                    figprintId,
                )
                if i + fingerprintLen >= len(line):
                    break

    def treatChunk(
        self,
        thisChunk,
        thisFileName,
        thisLine,
        thisrealposition,
        fingerprintLenght,
        figprintId,
    ):
        """generate fingerprints

        Parameters
        ----------
        thisChunk : int
            a round number which will split text size
            by the lengght of the fingerprint.
        thisFileName : str
            Real file name.
        thisLine : str
            current line we are working on.
        thisrealposition : int
            real position to evaluate.
        fingerprintLenght : int
            fingerprint length to generate.
        """

        fprint = thisLine[thisChunk : thisChunk + fingerprintLenght]
        if fprint in _CHUNKS_TO_IGNORE:
            return

        if fprint not in self.figprint.keys():
            nbFigprints = len(self.figprint) + 1
            self.figprint[fprint] = nbFigprints

        start = thisrealposition + thisChunk
        # NB fprint might be shorter than fingerprintLenght
        end = start + len(fprint)
        otherCandidate = FingerprintLocation(
            name=thisFileName.split("/")[-1],
            start=start,
            end=end,
        )

        figprintId.setdefault(self.figprint[fprint], []).append(otherCandidate)
