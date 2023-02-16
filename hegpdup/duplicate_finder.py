from collections import Counter

from intervaltree import IntervalTree

from .span import Span


class _Document:
    def __init__(self, id, spansByFingerprintId):
        self.id = id
        self.spansByFingerprintId = spansByFingerprintId


class Duplicate:
    __slots__ = (
        "sourceDocId",
        "sourceSpan",
        "targetSpan",
        "sourceFingerprintIds",
        "targetFingerprintIds",
    )

    def __init__(
        self,
        sourceDocId,
        sourceSpan,
        targetSpan,
        sourceFingerprintIds,
        targetFingerprintIds,
    ):
        self.sourceDocId = sourceDocId
        self.sourceSpan = sourceSpan
        self.targetSpan = targetSpan
        self.sourceFingerprintIds = sourceFingerprintIds
        self.targetFingerprintIds = targetFingerprintIds

    def __hash__(self):
        return hash(
            (
                self.sourceDocId,
                self.sourceSpan,
                self.targetSpan,
                self.sourceFingerprintIds,
                self.targetFingerprintIds,
            )
        )

    def __repr__(self):
        return f"Duplicate(sourceDocId={self.sourceDocId}, sourceSpan={self.sourceSpan!r}, targetSpan={self.targetSpan!r}, sourceFingerprintIds={self.sourceFingerprintIds}, targetFingerprintIds={self.targetFingerprintIds})"


class DuplicateFinder:
    def __init__(self, fingerprintBuilder, minNbFingerprints=2):
        self.minNbFingerprints = minNbFingerprints

        self.fingerprintBuilder = fingerprintBuilder
        self._docsById = dict()

    def findDuplicates(self, docId, docText):
        if docId in self._docsById:
            raise Exception(f"Already processed document with id {docId}")

        spansByFingerprintId = self.fingerprintBuilder.buildFingerprints(docText)
        doc = _Document(docId, spansByFingerprintId)

        comparisonTrees = {}
        for previousDoc in self._docsById.values():
            comparisonTree = self._buildComparisonTree(
                sourceDoc=previousDoc, targetDoc=doc
            )
            if comparisonTree is None:
                continue
            self._mergeOverlappingDuplicates(comparisonTree)

            comparisonTrees[previousDoc.id] = comparisonTree

        self._docsById[doc.id] = doc

        duplicates = [
            interval.data
            for tree in comparisonTrees.values()
            for interval in sorted(tree)
        ]

        return duplicates

    def _buildComparisonTree(self, sourceDoc, targetDoc):
        commonFingerprintIds = (
            sourceDoc.spansByFingerprintId.keys()
            & targetDoc.spansByFingerprintId.keys()
        )
        if len(commonFingerprintIds) < self.minNbFingerprints:
            return None

        comparisonTree = IntervalTree()
        # pour chaque fingerprint trouvé
        for fingerprintId in commonFingerprintIds:
            # pour chaque localisation du figerprint en from
            self._fillComparisonTree(
                sourceDoc, targetDoc, fingerprintId, comparisonTree
            )

        return comparisonTree

    def _fillComparisonTree(self, sourceDoc, targetDoc, fingerprintId, comparisonTree):
        for sourceSpan in sourceDoc.spansByFingerprintId[fingerprintId]:
            for targetSpan in targetDoc.spansByFingerprintId[fingerprintId]:
                duplicate = Duplicate(
                    sourceDocId=sourceDoc.id,
                    sourceSpan=sourceSpan,
                    targetSpan=targetSpan,
                    sourceFingerprintIds=[fingerprintId],
                    targetFingerprintIds=[fingerprintId],
                )
                comparisonTree[sourceSpan.start : sourceSpan.end] = duplicate

    def _mergeOverlappingDuplicates(self, comparisonTree):
        for interval in sorted(comparisonTree):
            self._mergeOverlappingDuplicatesAtInterval(interval, comparisonTree)

    def _mergeOverlappingDuplicatesAtInterval(self, interval, comparisonTree):
        overlappingIntervals = sorted(
            comparisonTree.overlap(interval.end - 1, interval.end + 1)
        )
        if len(overlappingIntervals) <= 1:
            return

        duplicates = [interval.data for interval in overlappingIntervals]

        for i in range(0, len(overlappingIntervals) - 1):
            prevDuplicate = duplicates[i]
            nextDuplicate = duplicates[i + 1]
            self._mergeDuplicates(
                prevDuplicate,
                nextDuplicate,
                comparisonTree,
            )

    def _mergeDuplicates(
        self,
        prevDuplicate,
        nextDuplicate,
        comparisonTree,
    ):
        if nextDuplicate.targetSpan.end < prevDuplicate.targetSpan.start:
            return

        sourceSpan = _mergeSpans(prevDuplicate.sourceSpan, nextDuplicate.sourceSpan)
        targetSpan = _mergeSpans(prevDuplicate.targetSpan, nextDuplicate.targetSpan)

        # ignore duplication if from/to spans end up having different lengths
        # after merge
        if sourceSpan.length != targetSpan.length:
            return

        targetFingerprintIds = (
            prevDuplicate.targetFingerprintIds + prevDuplicate.targetFingerprintIds
        )
        sourceFingerprintIds = (
            prevDuplicate.sourceFingerprintIds + prevDuplicate.sourceFingerprintIds
        )
        if not _compareCounter(targetFingerprintIds, sourceFingerprintIds):
            return

        mergedDuplicate = Duplicate(
            sourceDocId=prevDuplicate.sourceDocId,
            sourceSpan=sourceSpan,
            targetSpan=targetSpan,
            # should this be list(set((sourceFingerprintIds))?
            sourceFingerprintIds=list(set(targetFingerprintIds)),
            targetFingerprintIds=list(set(targetFingerprintIds)),
        )
        comparisonTree.remove_envelop(sourceSpan.start, sourceSpan.end)
        comparisonTree[sourceSpan.start : sourceSpan.end] = mergedDuplicate


# https://stackoverflow.com/questions/7828867/how-to-efficiently-compare-two-unordered-lists-not-sets-in-python
# O(n): The Counter() method is best (if your objects are hashable):
def _compareCounter(s, t):
    return Counter(s) == Counter(t)


def _mergeSpans(span1, span2):
    return Span(min(span1.start, span2.start), max(span1.end, span2.end))
