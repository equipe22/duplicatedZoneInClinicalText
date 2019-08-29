from intervaltree import IntervalTree
from itertools import product

from lib import intersection, compareCounter, returnUniq, sortBy, flat2gen
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(format="""%(asctime)s -- %(name)s - %(levelname)s :
                    %(message)s""",
                    datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.INFO)


class Document(object):

    def __init__(self, name):
        # fingerprint :{ 'located': {'start':0,'end':0}}
        self.name = name
        self.fingerprints = dict()
        # docID :{fingerprintlist}
        self.docsNeighbors = dict()
        # all fingerprint position

    def addFinger(self, thisFingerprint, duplicationDict):
        if thisFingerprint in self.fingerprints.keys():
            self.fingerprints[thisFingerprint].append({
                'name': duplicationDict["name"],
                'start': duplicationDict['start'],
                'end': duplicationDict['end']}
            )
            logger.debug("found duplicate site inside fingerprint")
            logger.debug(self.name)
            logger.debug(self.fingerprints[thisFingerprint])
        else:
            self.fingerprints[
                thisFingerprint] = [{
                    'name': duplicationDict["name"],
                    'start': duplicationDict['start'],
                    'end': duplicationDict['end']}]


class DocTrees(object):

    def __init__(self, name):
        # fingerprint :{ 'located': {'start':0,'end':0}}
        self.name = name
        self.docTree = dict()
        # a new tree where results are store by comparison
        self.resultTree = dict()

    def buildTree_comparisons(self, fingerprintDict):
        """Short summary.

        Parameters
        ----------
        figerprintsId : type
            Description of parameter `figerprintsId`.
        namesDict : type
            Description of parameter `namesDict`.

        Returns
        -------
        type
            Description of returned object.

        """
        for thisFingerprint in fingerprintDict.keys():
            if fingerprintDict[thisFingerprint]["frequence"] > 1:
                candidateList = [
                    (
                        ("name", thisCandidate["name"]),
                        ("start", thisCandidate["start"]),
                        ("end", thisCandidate["end"])
                    )
                    for thisCandidate in fingerprintDict[thisFingerprint][
                        "foundIn"]]
                candidateList = sortBy(returnUniq(candidateList), 0)
                # return uniq and an ordered list
                for thisCandidate in candidateList:
                    duplicationDict = dict(thisCandidate)
                    self.addACandidateToDocTree(
                        duplicationDict, thisFingerprint)
        return(self.docTree)

    def addACandidateToDocTree(self, duplicationDict, thisFingerprint):
        if duplicationDict["name"] not in self.docTree.keys():
            # create a document
            self.docTree[duplicationDict["name"]] = Document(
                duplicationDict["name"])
        # add a fingerprint
        self.docTree[duplicationDict["name"]].addFinger(
            thisFingerprint,
            duplicationDict)
        return(1)

    def mergeOverlap(self,  patientTexts,
                     rootPath, figprintId, nbFinger=2):
        # list of Docs name
        # [Doc00,Doc01, Doc02,Doc03]
        self.docsList = [key for key in self.docTree.keys()]
        logger.debug(self.docsList)
        self.docsList.sort()
        # fromIterator [Doc00,Doc01, Doc02]
        # toIterator [Doc01, Doc02, Doc03]
        for fromIterator, toIterator in product(range(0, len(self.docsList
                                                             )-1
                                                      ),
                                                range(1, len(self.docsList))):
            if fromIterator < toIterator:
                # if(self.docsList[fromIterator] != self.docsList[toIterator]):
                logger.debug(self.docsList[fromIterator], self.docsList[
                    toIterator])
                comparekey = [self.docsList[fromIterator], self.docsList[
                    toIterator]]
                logger.debug(comparekey)
                self.addComparisons(rootPath, fromIterator,
                                    toIterator, comparekey, figprintId,
                                    nbFinger)
                # if "_".join(comparekey) in resultTree.keys():
        logger.debug("DONE FIRST PART")
        return(self.resultTree)

    def addComparisons(self, keyRoot, fromIterator, toIterator,
                       comparekey, figprintId, nbFinger):
        fromFingerprints = [
            key for key in self.docTree[self.docsList[fromIterator]
                                        ].fingerprints.keys()]
        toFingerprints = [
            key for key in self.docTree[self.docsList[toIterator]
                                        ].fingerprints.keys()]
        # Get element which are in comon between two lists
        interSct = intersection(fromFingerprints, toFingerprints)
        logger.debug(interSct)
        if len(interSct) >= nbFinger:
            interSct.sort()
            if "_".join(comparekey) not in self.resultTree.keys():
                self.resultTree["_".join(comparekey)] = IntervalTree()
            # pour chaque fingerprint trouvé
            for thisFinger in interSct:
                # pour chaque localisation du figerprint en from
                logger.debug("######################################")
                logger.debug(thisFinger)
                logger.debug(self.docTree[self.docsList[fromIterator]
                                          ].fingerprints[thisFinger])
                logger.debug(figprintId[thisFinger])
                self.buildComparisons(fromIterator, toIterator,
                                      thisFinger, "_".join(comparekey))
        return(1)

    def buildComparisons(self, fromIterator, toIterator, thisFinger,
                         comparekey):
        for fromLocated in self.docTree[self.docsList[fromIterator]
                                        ].fingerprints[thisFinger]:
            # [{'located': {'start': 10172, 'end': 10212}}]
            fromPos = self.checkCandidate(fromIterator, fromLocated)
            for toLocated in self.docTree[self.docsList[toIterator]
                                          ].fingerprints[thisFinger]:
                toPos = self.checkCandidate(toIterator, toLocated)
                to_positions = {
                    "start": toPos[0],
                    "end": toPos[1],
                    "fingerprint": [thisFinger],
                    "fromFingerprint": [thisFinger]
                }
                self.resultTree[comparekey][fromPos[0]:fromPos[1]
                                            ] = to_positions
        return(1)

    def checkCandidate(self, pos, thisCandidate):
        if thisCandidate["name"] == self.docsList[pos]:
            start = thisCandidate["start"]
            end = thisCandidate["end"]
            return([start, end])
        else:
            return([])

    def expandOverlap(self, docInfo_R):
        logger.debug(self.resultTree.keys())
        logger.debug(len(self.resultTree.keys()))
        # keysss=sorted(self.resultTree.keys())
        for comparison in sorted(self.resultTree.keys()):
            # for it in range(0,10):
            # comparison=keysss[it]
            logger.debug(comparison)
            logger.debug(len(self.resultTree[comparison]))
            logger.debug("#############")
            for duplication in sorted(self.resultTree[comparison]):
                candidateOverlap = sorted(self.resultTree[
                    comparison].search(duplication.end-1,duplication.end+1))
                if len(candidateOverlap) > 1:
                    logger.debug("found a candidate")
                    logger.debug(candidateOverlap)
                    toAspirant = [
                        (this.data["start"], this.data["end"],
                         this.data["fromFingerprint"],
                         this.data["fingerprint"])
                        for this in candidateOverlap]
                    fromAspirant = [
                        (el.begin, el.end) for el in candidateOverlap]
                    for pos in range(0, len(fromAspirant)):
                        # the iterator is for from and to
                        if (pos+1 < len(toAspirant
                                        )) and (pos+1 < len(fromAspirant)):
                            self.addLeaf(fromAspirant, toAspirant,
                                         comparison, pos, docInfo_R)

        return(1)

    def addLeaf(self, fromAspirant, toAspirant, comparison,
                pos, docInfo_R):
        dataKey=comparison.split("_")
        sizeDoc1 = docInfo_R[dataKey[0]]
        sizeDoc2 = docInfo_R[dataKey[1]]
        positionFrom = (
            # start 0
            min(fromAspirant[pos][0], fromAspirant[pos+1][0]),
            # end 1
            max(fromAspirant[pos][1], fromAspirant[pos+1][1])
        )
        positionTo = (
            min(toAspirant[pos][0], toAspirant[pos+1][0]),
            max(toAspirant[pos][1], toAspirant[pos+1][1])
        )

        if(positionFrom[1]<= sizeDoc1 and positionFrom[0] <= sizeDoc1) and (positionTo[1]<= sizeDoc2 and positionTo[0] <= sizeDoc2):
            if(positionFrom[1]-positionFrom[0]) == (positionTo[1]-positionTo[0]):
                self.CheckCandidatesPositions(comparison, toAspirant, fromAspirant,positionFrom, positionTo, pos)
        return(1)

    def CheckCandidatesPositions(self, comparison, toAspirant, fromAspirant,
                                 positionFrom, positionTo, pos):
        if (toAspirant[pos+1][1] >= toAspirant[pos][0]):
            fingers = list(flat2gen([toAspirant[pos][-1], toAspirant[pos+1][-1]
                                     ]))
            fingers.sort()
            fromfingers = list(flat2gen([toAspirant[pos][-2], toAspirant[
                pos+1][-2]]))              
            fromfingers.sort()
            #~ print(fingers)
            #~ print(fromfingers)
            if compareCounter(fingers, fromfingers):
                to_positions = {
                    "start": positionTo[0],
                    "end": positionTo[1],
                    "fingerprint": returnUniq(fingers),
                    "fromFingerprint": returnUniq(fingers)
                }
                self.resultTree[comparison].remove_envelop(
                    positionFrom[0],
                    positionFrom[1])
                self.resultTree[
                    comparison][
                    positionFrom[0]:positionFrom[1]
                ] = to_positions
        return(1)
