from collections import Counter

from intervaltree import IntervalTree

from .span import Span


class Document:
    def __init__(self, name, fingerprints):
        self.name = name
        self.fingerprints = fingerprints


class Duplicate:
    __slots__ = (
        "sourceDocName",
        "sourceSpan",
        "targetSpan",
        "fingerprint",
        "fromFingerprint",
    )

    def __init__(
        self, sourceDocName, sourceSpan, targetSpan, fingerprint, fromFingerprint
    ):
        self.sourceDocName = sourceDocName
        self.sourceSpan = sourceSpan
        self.targetSpan = targetSpan
        self.fingerprint = fingerprint
        self.fromFingerprint = fromFingerprint

    def __hash__(self):
        return hash(
            (
                self.sourceDocName,
                self.sourceSpan,
                self.targetSpan,
                self.fingerprint,
                self.fromFingerprint,
            )
        )

    def __repr__(self):
        return f"Duplicate(sourceDocName={self.sourceDocName}, sourceSpan={self.sourceSpan!r}, targetSpan={self.targetSpan!r}, fingerprint={self.fingerprint}, fromFingerprint={self.fromFingerprint})"


class DuplicateFinder:
    def __init__(self, fingerprintBuilder, nbFinger=2):
        self.nbFinger = nbFinger

        self.fingerprintBuilder = fingerprintBuilder
        self.docTree = dict()

    def findDuplicates(self, name, text):
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

        duplicates = [
            interval.data
            for tree in comparisonTrees.values()
            for interval in sorted(tree)
        ]

        return duplicates

    def buildComparisonTree(self, docFrom, docTo):
        interSct = docFrom.fingerprints.keys() & docTo.fingerprints.keys()
        if len(interSct) < self.nbFinger:
            return None

        comparisonTree = IntervalTree()
        # pour chaque fingerprint trouvé
        for thisFinger in interSct:
            # pour chaque localisation du figerprint en from
            self.fillComparisonTree(docFrom, docTo, thisFinger, comparisonTree)

        return comparisonTree

    def fillComparisonTree(self, docFrom, docTo, thisFinger, comparisonTree):
        for fromLocated in docFrom.fingerprints[thisFinger]:
            for toLocated in docTo.fingerprints[thisFinger]:
                to_positions = Duplicate(
                    sourceDocName=docFrom.name,
                    sourceSpan=fromLocated,
                    targetSpan=toLocated,
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

        duplicates = [this.data for this in candidateOverlap]

        for pos in range(0, len(candidateOverlap) - 1):
            prevDuplicate = duplicates[pos]
            nextDuplicate = duplicates[pos + 1]
            self.addLeaf(
                prevDuplicate,
                nextDuplicate,
                comparisonTree,
            )

    def addLeaf(
        self,
        prevDuplicate,
        nextDuplicate,
        comparisonTree,
    ):
        if nextDuplicate.targetSpan.end < prevDuplicate.targetSpan.start:
            return

        positionFrom = _mergeSpans(prevDuplicate.sourceSpan, nextDuplicate.sourceSpan)
        positionTo = _mergeSpans(prevDuplicate.targetSpan, nextDuplicate.targetSpan)

        # ignore duplication if from/to spans end up having different lengths
        # after merge
        if positionFrom.length != positionTo.length:
            return

        fingers = prevDuplicate.fingerprint + prevDuplicate.fingerprint
        fromfingers = prevDuplicate.fromFingerprint + prevDuplicate.fromFingerprint
        if not _compareCounter(fingers, fromfingers):
            return

        to_positions = Duplicate(
            sourceDocName=prevDuplicate.sourceDocName,
            sourceSpan=positionFrom,
            targetSpan=positionTo,
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
