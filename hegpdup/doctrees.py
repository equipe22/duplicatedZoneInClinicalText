from itertools import product
import logging

from intervaltree import IntervalTree

from .lib import intersection, compareCounter, returnUniq, flat2gen


logger = logging.getLogger(__name__)
logging.basicConfig(
    format="""%(asctime)s -- %(name)s - %(levelname)s :
                    %(message)s""",
    datefmt="%m/%d/%Y %I:%M:%S %p",
    level=logging.INFO,
)


class Document:
    def __init__(self, name):
        self.name = name
        self.fingerprints = dict()
        # docID :{fingerprintlist}

    def addFinger(self, thisFingerprint, location):
        if thisFingerprint in self.fingerprints.keys():
            self.fingerprints[thisFingerprint].append(location)
            logger.debug("found duplicate site inside fingerprint")
            logger.debug(self.name)
            logger.debug(self.fingerprints[thisFingerprint])
        else:
            self.fingerprints[thisFingerprint] = [location]


class Duplicate:
    __slots__ = "start", "end", "fingerprint", "fromFingerprint"

    def __init__(self, start, end, fingerprint, fromFingerprint):
        self.start = start
        self.end = end
        self.fingerprint = fingerprint
        self.fromFingerprint = fromFingerprint

    def __hash__(self):
        return hash(
            (self.name, self.start, self.end, self.fingerprint, self.fromFingerprint)
        )

    def __repr__(self):
        return f"Duplicate(start={self.start}, end={self.end}, fingerprint={self.fingerprint}, fromFingerprint={self.fromFingerprint})"


class Span:
    __slots__ = "start", "end"

    def __init__(self, start, end):
        self.start = start
        self.end = end

    def __hash__(self):
        return hash(self.start, self.end)

    def __repr__(self):
        return f"Span(start={self.start}, end={self.end})"


class DocTrees:
    def __init__(self):
        self.docTree = dict()
        # a new tree where results are store by comparison
        self.resultTree = dict()

    def buildTree_comparisons(self, fingerprintDict):
        for thisFingerprint in fingerprintDict.keys():
            if fingerprintDict[thisFingerprint].frequence > 1:
                candidateList = sorted(
                    returnUniq(fingerprintDict[thisFingerprint].foundIn),
                    key=lambda l: l.name,
                )
                # return uniq and an ordered list
                for thisCandidate in candidateList:
                    self.addACandidateToDocTree(thisCandidate, thisFingerprint)

    def addACandidateToDocTree(self, location, thisFingerprint):
        if location.name not in self.docTree.keys():
            # create a document
            self.docTree[location.name] = Document(location.name)
        # add a fingerprint
        self.docTree[location.name].addFinger(thisFingerprint, location)

    def mergeOverlap(self, figprintId, nbFinger=2):
        # list of Docs name
        # [Doc00,Doc01, Doc02,Doc03]
        self.docsList = [key for key in self.docTree.keys()]
        logger.debug(self.docsList)
        self.docsList.sort()
        # fromIterator [Doc00,Doc01, Doc02]
        # toIterator [Doc01, Doc02, Doc03]
        for fromIterator, toIterator in product(
            range(0, len(self.docsList) - 1), range(1, len(self.docsList))
        ):
            if fromIterator < toIterator:
                logger.debug(self.docsList[fromIterator], self.docsList[toIterator])
                comparekey = [self.docsList[fromIterator], self.docsList[toIterator]]
                logger.debug(comparekey)
                self.addComparisons(
                    fromIterator, toIterator, comparekey, figprintId, nbFinger
                )
        logger.debug("DONE FIRST PART")

    def addComparisons(
        self, fromIterator, toIterator, comparekey, figprintId, nbFinger
    ):
        fromFingerprints = [
            key for key in self.docTree[self.docsList[fromIterator]].fingerprints.keys()
        ]
        toFingerprints = [
            key for key in self.docTree[self.docsList[toIterator]].fingerprints.keys()
        ]
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
                logger.debug(
                    self.docTree[self.docsList[fromIterator]].fingerprints[thisFinger]
                )
                logger.debug(figprintId[thisFinger])
                self.buildComparisons(
                    fromIterator, toIterator, thisFinger, "_".join(comparekey)
                )

    def buildComparisons(self, fromIterator, toIterator, thisFinger, comparekey):
        for fromLocated in self.docTree[self.docsList[fromIterator]].fingerprints[
            thisFinger
        ]:
            fromPos = self.checkCandidate(fromIterator, fromLocated)
            for toLocated in self.docTree[self.docsList[toIterator]].fingerprints[
                thisFinger
            ]:
                toPos = self.checkCandidate(toIterator, toLocated)
                to_positions = Duplicate(
                    start=toPos[0],
                    end=toPos[1],
                    fingerprint=[thisFinger],
                    fromFingerprint=[thisFinger],
                )
                self.resultTree[comparekey][fromPos[0] : fromPos[1]] = to_positions

    def checkCandidate(self, pos, thisCandidate):
        if thisCandidate.name == self.docsList[pos]:
            start = thisCandidate.start
            end = thisCandidate.end
            return [start, end]
        else:
            return []

    def expandOverlap(self, docInfo_R):
        logger.debug(self.resultTree.keys())
        logger.debug(len(self.resultTree.keys()))
        for comparison in sorted(self.resultTree.keys()):
            logger.debug(comparison)
            logger.debug(len(self.resultTree[comparison]))
            logger.debug("#############")
            for duplication in sorted(self.resultTree[comparison]):
                candidateOverlap = sorted(
                    self.resultTree[comparison].overlap(
                        duplication.end - 1, duplication.end + 1
                    )
                )
                if len(candidateOverlap) > 1:
                    logger.debug("found a candidate")
                    logger.debug(candidateOverlap)
                    toAspirant = [this.data for this in candidateOverlap]
                    fromAspirant = [Span(el.begin, el.end) for el in candidateOverlap]
                    for pos in range(0, len(fromAspirant)):
                        # the iterator is for from and to
                        if (pos + 1 < len(toAspirant)) and (
                            pos + 1 < len(fromAspirant)
                        ):
                            self.addLeaf(
                                fromAspirant, toAspirant, comparison, pos, docInfo_R
                            )

    def addLeaf(self, fromAspirant, toAspirant, comparison, pos, docInfo_R):
        dataKey = comparison.split("_")
        sizeDoc1 = docInfo_R[dataKey[0]]
        sizeDoc2 = docInfo_R[dataKey[1]]
        positionFrom = Span(
            min(fromAspirant[pos].start, fromAspirant[pos + 1].start),
            max(fromAspirant[pos].end, fromAspirant[pos + 1].end),
        )
        positionTo = Span(
            min(toAspirant[pos].start, toAspirant[pos + 1].start),
            max(toAspirant[pos].end, toAspirant[pos + 1].end),
        )

        if (positionFrom.end <= sizeDoc1 and positionFrom.start <= sizeDoc1) and (
            positionTo.end <= sizeDoc2 and positionTo.start <= sizeDoc2
        ):
            if (positionFrom.end - positionFrom.start) == (
                positionTo.end - positionTo.start
            ):
                self.CheckCandidatesPositions(
                    comparison, toAspirant, positionFrom, positionTo, pos
                )

    def CheckCandidatesPositions(
        self, comparison, toAspirant, positionFrom, positionTo, pos
    ):
        if toAspirant[pos + 1].end >= toAspirant[pos].start:
            fingers = list(
                flat2gen([toAspirant[pos].fingerprint, toAspirant[pos + 1].fingerprint])
            )
            fingers.sort()
            fromfingers = list(
                flat2gen(
                    [
                        toAspirant[pos].fromFingerprint,
                        toAspirant[pos + 1].fromFingerprint,
                    ]
                )
            )
            fromfingers.sort()
            if compareCounter(fingers, fromfingers):
                to_positions = Duplicate(
                    start=positionTo.start,
                    end=positionTo.end,
                    fingerprint=returnUniq(fingers),
                    # should this be returnUniq(fromfingers)d?
                    fromFingerprint=returnUniq(fingers),
                )
                self.resultTree[comparison].remove_envelop(
                    positionFrom.start, positionFrom.end
                )
                self.resultTree[comparison][
                    positionFrom.start : positionFrom.end
                ] = to_positions
