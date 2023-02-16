from collections import Counter
import itertools
import logging

from intervaltree import IntervalTree


logger = logging.getLogger(__name__)
logging.basicConfig(
    format="""%(asctime)s -- %(name)s - %(levelname)s :
                    %(message)s""",
    datefmt="%m/%d/%Y %I:%M:%S %p",
    level=logging.INFO,
)


class Document:
    def __init__(self, name, fingerprints):
        self.name = name
        self.fingerprints = fingerprints


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

    @property
    def length(self):
        return self.end - self.start

    def __hash__(self):
        return hash(self.start, self.end)

    def __repr__(self):
        return f"Span(start={self.start}, end={self.end})"


class DuplicateFinder:
    def __init__(self, fingerprintBuilder, nbFinger=2):
        self.nbFinger = nbFinger

        self.fingerprintBuilder = fingerprintBuilder
        self.docTree = dict()
        # a new tree where results are store by comparison
        self.resultTree = dict()

    def buildTree_comparisons(self, filesInformation):
        for i, text in enumerate(filesInformation):
            name = f"D{i}"
            self.addDocTree(name, text)

        self.mergeOverlap()
        self.expandOverlap()

    def addDocTree(self, name, text):
        fingerprintDict = self.fingerprintBuilder.generateFingerprints(name, text)
        doc = Document(name, fingerprintDict)
        self.docTree[doc.name] = doc

    def mergeOverlap(self):
        # list of Docs name
        # [Doc00,Doc01, Doc02,Doc03]
        docNames = sorted(self.docTree.keys())
        logger.debug(docNames)

        for docNameFrom, docNameTo in itertools.combinations(docNames, 2):
            logger.debug([docNameFrom, docNameTo])
            docFrom = self.docTree[docNameFrom]
            docTo = self.docTree[docNameTo]

            self.addComparisons(docFrom, docTo)
        logger.debug("DONE FIRST PART")

    def addComparisons(self, docFrom, docTo):
        interSct = docFrom.fingerprints.keys() & docTo.fingerprints.keys()
        logger.debug(interSct)
        if len(interSct) < self.nbFinger:
            return

        comparekey = (docFrom.name, docTo.name)
        comparisonTree = self.resultTree.get(comparekey)
        if comparisonTree is None:
            comparisonTree = IntervalTree()
            self.resultTree[comparekey] = comparisonTree
        # pour chaque fingerprint trouvé
        for thisFinger in interSct:
            # pour chaque localisation du figerprint en from
            logger.debug("######################################")
            logger.debug(thisFinger)
            logger.debug(docFrom.fingerprints[thisFinger])
            self.buildComparisons(docFrom, docTo, thisFinger, comparisonTree)

    def buildComparisons(self, docFrom, docTo, thisFinger, comparisonTree):
        for fromLocated in docFrom.fingerprints[thisFinger]:
            for toLocated in docTo.fingerprints[thisFinger]:
                to_positions = Duplicate(
                    start=toLocated.start,
                    end=toLocated.end,
                    fingerprint=[thisFinger],
                    fromFingerprint=[thisFinger],
                )
                comparisonTree[fromLocated.start : fromLocated.end] = to_positions

    def expandOverlap(self):
        logger.debug(self.resultTree.keys())
        logger.debug(len(self.resultTree.keys()))

        for comparison in sorted(self.resultTree.keys()):
            comparisonTree = self.resultTree[comparison]
            logger.debug(comparison)
            logger.debug(len(comparisonTree))
            logger.debug("#############")
            for duplication in sorted(comparisonTree):
                self.expandDuplication(duplication, comparisonTree)

    def expandDuplication(self, duplication, comparisonTree):
        candidateOverlap = sorted(
            comparisonTree.overlap(duplication.end - 1, duplication.end + 1)
        )
        if len(candidateOverlap) <= 1:
            return

        logger.debug("found a candidate")
        logger.debug(candidateOverlap)
        toAspirant = [this.data for this in candidateOverlap]
        fromAspirant = [Span(el.begin, el.end) for el in candidateOverlap]

        for pos in range(0, len(candidateOverlap) - 1):
            self.addLeaf(fromAspirant, toAspirant, comparisonTree, pos)

    def addLeaf(self, fromAspirant, toAspirant, comparisonTree, pos):
        positionFrom = _mergeSpans(fromAspirant[pos], fromAspirant[pos + 1])
        positionTo = _mergeSpans(toAspirant[pos], toAspirant[pos + 1])

        # ignore duplication if from/to spans end up having different lengths
        # after merge
        if positionFrom.length != positionTo.length:
            return

        if toAspirant[pos + 1].end < toAspirant[pos].start:
            return

        fingers = toAspirant[pos].fingerprint + toAspirant[pos + 1].fingerprint
        fromfingers = (
            toAspirant[pos].fromFingerprint + toAspirant[pos + 1].fromFingerprint
        )
        if not _compareCounter(fingers, fromfingers):
            return

        to_positions = Duplicate(
            start=positionTo.start,
            end=positionTo.end,
            fingerprint=list(set(fingers)),
            # should this be list(set((fromfingers))?
            fromFingerprint=list(set(fingers)),
        )
        comparisonTree.remove_envelop(positionFrom.start, positionFrom.end)
        comparisonTree[positionFrom.start : positionFrom.end] = to_positions


# https://stackoverflow.com/questions/7828867/how-to-efficiently-compare-two-unordered-lists-not-sets-in-python
# O(n): The Counter() method is best (if your objects are hashable):
def _compareCounter(s, t):
    return Counter(s) == Counter(t)


def _mergeSpans(span1, span2):
    return Span(min(span1.start, span2.start), max(span1.end, span2.end))
