from intervaltree import IntervalTree

from .span import Span


class _Document:
    def __init__(self, id, spansByFingerprintId):
        self.id = id
        self.spansByFingerprintId = spansByFingerprintId


class Duplicate:
    """
    Represents a duplicated part between 2 documents,
    designated by characters spans
    """

    __slots__ = "sourceDocId", "sourceSpan", "targetSpan", "fingerprintIds"

    def __init__(self, sourceDocId, sourceSpan, targetSpan, fingerprintIds):
        """
        Parameters
        ----------
        sourceDocId: str
            Identifier of the source document
        sourceSpan: Span
            Duplicated character span in the source document
        targetSpan: Span
            Duplicated character span in the target document
        fingerprintIds: List[int]
            Common fingerprint ids in source and target parts
        """

        self.sourceDocId = sourceDocId
        self.sourceSpan = sourceSpan
        self.targetSpan = targetSpan
        self.fingerprintIds = fingerprintIds

    def __hash__(self):
        return hash(
            (self.sourceDocId, self.sourceSpan, self.targetSpan, self.fingerprintIds)
        )

    def __repr__(self):
        return f"Duplicate(sourceDocId={self.sourceDocId}, sourceSpan={self.sourceSpan!r}, targetSpan={self.targetSpan!r}, fingerprintIds={self.fingerprintIds})"


class DuplicateFinder:
    """
    Finds duplicated parts in a set of documents.

    Relies on a `FingerprintBuilder` to generate fingerprints for documents,
    then identifies parts with common fingerprints between each document.
    """

    def __init__(self, fingerprintBuilder, minNbFingerprints=2):
        """
        Parameters
        ----------
        fingerprintBuilder: FingerprintBuilder
            `FingerprintBuilder` instance to use to generate fingerprints for
            each document
        minNbFingerprints: int
            Minimum number of common fingerprints between 2 documents, under which
            the `DuplicateFinder` won't attempt to find any duplicates
        """

        self.minNbFingerprints = minNbFingerprints
        self.fingerprintBuilder = fingerprintBuilder

        # mapping of previously seen documents, by id
        self._docsById = dict()

    def findDuplicates(self, docId, docText):
        """
        Look for parts in `docText` in common with previously seen documents,
        and return then as `Duplicate` objects.

        To compare "newer" documents with "older" ones, make sure to call this
        by increasing date/time.

        Parameters
        ----------
        docId: str
            Unique identifier of the document
        docText: str
            Text of the document

        Returns
        -------
        Dict[str, List[Duplicate]]
            For each previously seen document that has parts in common with
            `docText`, a list of Duplicate` objects designated corresponding
            character spans. The key of the mapping is the source document id
        """

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
        """
        Build a interval tree comparing potential source and target documents,
        using source spans as interval boundaries and `Duplicate` objects as
        interval values.

        One `Duplicate` object will be created the combination of all
        appearances of common fingerprints in the source and target documents.

        Parameters
        ----------
        sourceDoc: Document
            Document to be used as source
        targetDoc: Document
            Document to be used as target

        Returns
        -------
        IntervalTree:
            Comparison interval tree
        """

        commonFingerprintIds = (
            sourceDoc.spansByFingerprintId.keys()
            & targetDoc.spansByFingerprintId.keys()
        )
        if len(commonFingerprintIds) < self.minNbFingerprints:
            return None

        comparisonTree = IntervalTree()
        for fingerprintId in commonFingerprintIds:
            # add duplicates for each common fingerprints
            self._fillComparisonTree(
                sourceDoc, targetDoc, fingerprintId, comparisonTree
            )

        return comparisonTree

    def _fillComparisonTree(
        self, sourceDoc, targetDoc, commonFingerprintId, comparisonTree
    ):
        """
        Populate a comparison interval tree with `Duplicate` objects for the
        combination of all appearances of a given fingerprint in the source and
        target documents.

        Parameters
        ----------
        sourceDoc: Document
            Document to be used as source
        targetDoc: Document
            Document to be used as target
        commonFingerprintId: int
            A fingerprint appearing in both documents
        comparisonTree: IntervalTree
            The comparison tree to update
        """

        # create duplicate for all combinations of source and target spans for a given common fingerprint
        for sourceSpan in sourceDoc.spansByFingerprintId[commonFingerprintId]:
            for targetSpan in targetDoc.spansByFingerprintId[commonFingerprintId]:
                duplicate = Duplicate(
                    sourceDocId=sourceDoc.id,
                    sourceSpan=sourceSpan,
                    targetSpan=targetSpan,
                    fingerprintIds=[commonFingerprintId],
                )
                comparisonTree[sourceSpan.start : sourceSpan.end] = duplicate

    def _mergeOverlappingDuplicates(self, comparisonTree):
        """
        Merge overlapping or consecutive intervals and their corresponding
        `Duplicate` objects in an comparison interval tree.

        Parameters
        ----------
        comparisonTree: IntervalTree
            The comparison tree to update
        """

        for interval in sorted(comparisonTree):
            self._mergeOverlappingDuplicatesAtInterval(interval, comparisonTree)

    def _mergeOverlappingDuplicatesAtInterval(self, interval, comparisonTree):
        """
        Merge overlapping or consecutive intervals and their corresponding
        `Duplicate` objects in an comparison interval tree at a specific interval

        Parameters
        ----------
        interval: Interval
            The interval of the comparison tree to consider
        comparisonTree: IntervalTree
            The comparison tree to update
        """

        overlappingIntervals = sorted(
            comparisonTree.overlap(interval.end - 1, interval.end + 1)
        )
        if len(overlappingIntervals) <= 1:
            return

        duplicates = [interval.data for interval in overlappingIntervals]

        for i in range(0, len(overlappingIntervals) - 1):
            prevDuplicate = duplicates[i]
            nextDuplicate = duplicates[i + 1]
            mergedDuplicate = _mergeDuplicates(prevDuplicate, nextDuplicate)
            if mergedDuplicate is None:
                continue

            # remove all intervals and their associated Duplicate objects
            # (will include the 2 we merged but maybe also others!)
            # note that we are mutating the interval tree but we already extracted some intervals
            # from it which may not be valid anymore
            mergedSourceSpan = mergedDuplicate.sourceSpan
            comparisonTree.remove_envelop(mergedSourceSpan.start, mergedSourceSpan.end)
            comparisonTree[
                mergedSourceSpan.start : mergedSourceSpan.end
            ] = mergedDuplicate


def _mergeDuplicates(prevDuplicate, nextDuplicate):
    """Merge 2 duplicates into a new `Duplicate` object covering their source and target spans"""

    if nextDuplicate.targetSpan.end < prevDuplicate.targetSpan.start:
        return None

    sourceSpan = _mergeSpans(prevDuplicate.sourceSpan, nextDuplicate.sourceSpan)
    targetSpan = _mergeSpans(prevDuplicate.targetSpan, nextDuplicate.targetSpan)

    # ignore duplication if from/to spans end up having different lengths
    # after merge
    if sourceSpan.length != targetSpan.length:
        return None

    fingerprintIds = list(
        set(prevDuplicate.fingerprintIds + prevDuplicate.fingerprintIds)
    )

    mergedDuplicate = Duplicate(
        sourceDocId=prevDuplicate.sourceDocId,
        sourceSpan=sourceSpan,
        targetSpan=targetSpan,
        fingerprintIds=fingerprintIds,
    )
    return mergedDuplicate


def _mergeSpans(span1, span2):
    return Span(min(span1.start, span2.start), max(span1.end, span2.end))
