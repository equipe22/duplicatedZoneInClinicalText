from collections import Counter
import logging

from intervaltree import IntervalTree

from .span import Span


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


class DuplicateFinder:
    def __init__(self, fingerprintBuilder, nbFinger=2):
        self.nbFinger = nbFinger

        self.fingerprintBuilder = fingerprintBuilder
        self.docTree = dict()

    def buildComparisonTrees(self, name, text):
        if name in self.docTree:
            raise Exception(f"Already processed document with name {name}")

        fingerprintDict = self.fingerprintBuilder.buildFingerprints(text)
        doc = Document(name, fingerprintDict)

        comparisonTrees = {}
        for previousDoc in self.docTree.values():
            comparisonTree = self.buildComparisonTree(docFrom=previousDoc, docTo=doc)
            if comparisonTree is None:
                continue
            self.expandComparisonTree(comparisonTree)

            comparisonTrees[previousDoc.name] = comparisonTree

        self.docTree[doc.name] = doc

        return comparisonTrees

    def buildComparisonTree(self, docFrom, docTo):
        interSct = docFrom.fingerprints.keys() & docTo.fingerprints.keys()
        logger.debug(interSct)
        if len(interSct) < self.nbFinger:
            return None

        comparisonTree = IntervalTree()
        # pour chaque fingerprint trouvé
        for thisFinger in interSct:
            # pour chaque localisation du figerprint en from
            logger.debug("######################################")
            logger.debug(thisFinger)
            logger.debug(docFrom.fingerprints[thisFinger])
            self.fillComparisonTree(docFrom, docTo, thisFinger, comparisonTree)

        return comparisonTree

    def fillComparisonTree(self, docFrom, docTo, thisFinger, comparisonTree):
        for fromLocated in docFrom.fingerprints[thisFinger]:
            for toLocated in docTo.fingerprints[thisFinger]:
                to_positions = Duplicate(
                    start=toLocated.start,
                    end=toLocated.end,
                    fingerprint=[thisFinger],
                    fromFingerprint=[thisFinger],
                )
                comparisonTree[fromLocated.start : fromLocated.end] = to_positions

    def expandComparisonTree(self, comparisonTree):
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
