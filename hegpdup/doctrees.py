import itertools
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
            if fingerprintDict[thisFingerprint].foundIn:
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
        docNames = sorted(self.docTree.keys())
        logger.debug(docNames)

        for docNameFrom, docNameTo in itertools.combinations(docNames, 2):
            logger.debug([docNameFrom, docNameTo])
            docFrom = self.docTree[docNameFrom]
            docTo = self.docTree[docNameTo]

            self.addComparisons(docFrom, docTo, figprintId, nbFinger)
        logger.debug("DONE FIRST PART")

    def addComparisons(self, docFrom, docTo, figprintId, nbFinger):
        fromFingerprints = [key for key in docFrom.fingerprints.keys()]
        toFingerprints = [key for key in docTo.fingerprints.keys()]
        # Get element which are in comon between two lists
        interSct = intersection(fromFingerprints, toFingerprints)
        logger.debug(interSct)
        if len(interSct) >= nbFinger:
            interSct.sort()
            comparekey = (docFrom.name, docTo.name)
            if comparekey not in self.resultTree.keys():
                self.resultTree[comparekey] = IntervalTree()
            # pour chaque fingerprint trouvé
            for thisFinger in interSct:
                # pour chaque localisation du figerprint en from
                logger.debug("######################################")
                logger.debug(thisFinger)
                logger.debug(docFrom.fingerprints[thisFinger])
                logger.debug(figprintId[thisFinger])
                self.buildComparisons(docFrom, docTo, thisFinger, comparekey)

    def buildComparisons(self, docFrom, docTo, thisFinger, comparekey):
        for fromLocated in docFrom.fingerprints[thisFinger]:
            for toLocated in docTo.fingerprints[thisFinger]:
                to_positions = Duplicate(
                    start=toLocated.start,
                    end=toLocated.end,
                    fingerprint=[thisFinger],
                    fromFingerprint=[thisFinger],
                )
                self.resultTree[comparekey][
                    fromLocated.start : fromLocated.end
                ] = to_positions

    def expandOverlap(self):
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
                            self.addLeaf(fromAspirant, toAspirant, comparison, pos)

    def addLeaf(self, fromAspirant, toAspirant, comparison, pos):
        positionFrom = Span(
            min(fromAspirant[pos].start, fromAspirant[pos + 1].start),
            max(fromAspirant[pos].end, fromAspirant[pos + 1].end),
        )
        positionTo = Span(
            min(toAspirant[pos].start, toAspirant[pos + 1].start),
            max(toAspirant[pos].end, toAspirant[pos + 1].end),
        )

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
