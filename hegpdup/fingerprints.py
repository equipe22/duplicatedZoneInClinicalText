import codecs
from os import path


class Fingerprints(object):
    # thisFolder, fingerprintList, orf

    def __init__(self, fingerprintList, orf, fileInformations):
        """Create object Fingerprints which contains all
        docs fingerprints for a patient fingerprint.

        Parameters
        ----------
        fingerprintList : [ int]
            list of fingerprint length.
        orf : int
            define the open reading frame length. the size of the shift
            when a text is read.
        fileInformations : list
            the attribute from DuplicationMetaData object. It contains list
            of patient files.

        Returns
        -------
        type object
            retured Fingerprints object.

        """
        # self.thisFolder = thisFolder
        self.fingerprintList = fingerprintList
        self.orf = orf
        # contains list of fingerprint
        self.figprint = dict()
        self.figprintId = dict()
        self.generateFingerprint(fileInformations)
        # self.figprint,self.figprintId = generateFingerprint

    def generateFingerprint(self, fileInformations):
        """Main script to generate Fingerprint.

        Parameters
        ----------
        fileInformations : list
            the attribute from DuplicationMetaData object. It contains list
            of patient files.
        Returns
        -------
        type
             set the figprint and figprintId attributes.

        """
        # vectors of vector index by fingerprint
        # maybe add a dictionnary of position
        # fileVectors = defaultdict(list)
        # patientFiles = listdir(thisFolder)
        figCounter = 0
        for thisfile in range(0, len(fileInformations)):
            data = fileInformations[thisfile]
            # ~ print(data)
            # ~ print(thisfile)
            # found the right position in text
            realposition = 0
            # Cadre de lecture
            # for line in data:
            #     print(line)
            # gere le multiline
            for linePosition in range(0, min(self.orf, len(data))):
                # split the text in n slice in chunck
                # line = "".join(data[linePosition:linePosition+2])
                line = "".join(
                    data[linePosition:]
                )  # for the demo break is needed because it generate noise need fix
                # print("chunks "+str(chunks))
                # ~ print("line "+str(line))
                # gere cadre de lecture[0 et +1]
                figCounter = self.createChunks(
                    line, realposition, figCounter, "D" + str(thisfile)
                )
                # Update linePosition value
                realposition = realposition + len(data[linePosition])
                #  for the demo break is needed because it generate noise need fix
        return 1

    def createChunks(self, line, realposition, figCounter, thisfile):
        """For a given line, create the appropriate
        text chunks to generate fingerprint.

        Parameters
        ----------
        line : str
            a doc line.
        realposition : int
            real text position.
        figCounter : int
            fingerprint id.
        thisfile :tuple
            contains path to the file to work on.

        Returns
        -------
        type int
            return an updated figCounter .

        """
        # print("chunks "+str(chunks))
        # gere cadre de lecture[0 et +1]
        for fingerprintLen in self.fingerprintList:
            listCadreLecture = range(0, len(line), self.orf)
            # for cadreDeLecture in listCadreLecture:
            # chunks = len(line[cadreDeLecture:]) / fingerprintLen
            figCounter = self.treatChunks(
                listCadreLecture,
                thisfile,
                line,
                realposition,
                figCounter,
                fingerprintLen,
            )
        return figCounter

    def treatChunks(
        self,
        thisChunks,
        thisFileName,
        thisLine,
        thisrealposition,
        thisFingerCounter,
        fingerprintLenght,
    ):
        """generate fingerprints and update the figprint_counter.

        Parameters
        ----------
        thisChunks : int
            a round number which will split text size
            by the lengght of the fingerprint.
        thisFileName : str
            Real file name.
        thisLine : str
            current line we are working on.
        thisrealposition : int
            real position to evaluate.
        thisFingerCounter : int
            the figerprint ID.
        fingerprintLenght : int
            fingerprint length to generate.

        Returns
        -------
        type int
            return an updated thisFingerCounter.
        """
        for i in thisChunks:
            # beginF = cadre + (i * fingerprintLenght)
            beginF = i
            endF = beginF + fingerprintLenght
            fprint = thisLine[beginF:endF]
            # start = cadre + thisrealposition + beginF
            start = thisrealposition + beginF
            end = start + fingerprintLenght
            # ~ print(fprint)
            if fprint not in ["\n", "\r\n"]:
                # if fprint not in ['\n', '\r\n']:
                if not fprint.lower() in self.figprint.keys():
                    # figprint_str = [figprint_counter,frequence]
                    thisFingerCounter += 1
                    self.figprint[fprint.lower()] = [thisFingerCounter, 0]
                    tmpDict = {
                        "fingerprint": fprint.lower(),
                        "hashkey": fprint.lower(),
                        "frequence": 0,
                        "foundIn": [],
                    }
                    self.figprintId[thisFingerCounter] = tmpDict
                    ########
                self.figprint[fprint.lower()][-1] += 1
                self.figprintId[self.figprint[fprint.lower()][0]][
                    "frequence"
                ] = self.figprint[fprint.lower()][-1]
                otherCandidate = {
                    "name": thisFileName.split("/")[-1],
                    "start": start,
                    "end": end,
                }
                self.figprintId[self.figprint[fprint.lower()][0]]["foundIn"].append(
                    otherCandidate
                )
        return thisFingerCounter
