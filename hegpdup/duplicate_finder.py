from enum import Enum

try:
    import intervaltree as it

    _HAS_INTERVAL_TREE = True
except ImportError:
    _HAS_INTERVAL_TREE = False

try:
    from ncls import NCLS
    import numpy as np

    _HAS_NCLS = True
except ImportError:
    _HAS_NCLS = False

from .span import Span


class _Document:
    """Fingerprinted document"""

    def __init__(self, id, spansByFingerprint):
        """
        Parameters
        ----------
        id: str
            Identifier of the document
        spansByFingerprint: Dict[str, List[Span]]
            Fingerprinted spans of the document, organized by fingerprint.
            This is used to easily get all spans of a source document having the
            same fingerprint as the span of a target document.
        """

        self.id = id
        self.spansByFingerprint = spansByFingerprint


class Duplicate:
    """
    Represents a duplicated part between 2 documents,
    designated by characters spans
    """

    __slots__ = "sourceDocId", "sourceSpan", "targetSpan", "length"

    def __init__(self, sourceDocId, sourceSpan, targetSpan):
        """
        Parameters
        ----------
        sourceDocId: str
            Identifier of the source document
        sourceSpan: Span
            Duplicated character span in the source document
        targetSpan: Span
            Duplicated character span in the target document. Must be same
            length as `sourceSpan`
        """

        assert sourceSpan.length == targetSpan.length

        self.sourceDocId = sourceDocId
        self.sourceSpan = sourceSpan
        self.targetSpan = targetSpan
        self.length = targetSpan.length

    def __repr__(self):
        return f"Duplicate(sourceDocId={self.sourceDocId}, sourceSpan={self.sourceSpan!r}, targetSpan={self.targetSpan!r})"


class TreeBackend(Enum):
    """Available backends to use for overlap trees. Using NCLS might improve
    performance"""

    NONE = "NONE"
    INTERVAL_TREE = "INTERVAL_TREE"
    NCLS = "NCLS"


class DuplicateFinder:
    """
    Finds duplicated parts in a set of documents.

    Relies on a fingerprint builder to generate fingerprints for each document,
    then identifies common consecutive fingerprints between documents.
    """

    def __init__(self, fingerprintBuilder, minDuplicateLength=2, treeBackend=None):
        """
        Parameters
        ----------
        fingerprintBuilder: Union[CharFingerprintBuilder, WordFingerprintBuilder]
            Fingerprint builder instance to use to generate fingerprints for
            each document
        minDuplicateLength: int
            Minimum number of characters in duplicates. Should be set in
            accordance with the `fingerprintLength` of the fingerprint builder,
            cf docstrings of `CharFingerprintBuilder` and
            `WordFingerprintBuilder`
        treeBackend: Optional[TreeBackend]
            Backend to use for overlap trees. If `None` provided, we will select
            NCLS or INTERVAL_TREE (in that order) if they appear to be
            available. Using NCLS should provide best performance. INTERVAL_TREE
            performance can be inferior to not using overlap trees at all.
        """

        if treeBackend is None:
            if _HAS_NCLS:
                treeBackend = TreeBackend.NCLS
            elif _HAS_INTERVAL_TREE:
                treeBackend = TreeBackend.INTERVAL_TREE
            else:
                treeBackend = TreeBackend.NONE

        self.fingerprintBuilder = fingerprintBuilder
        self.minDuplicateLength = minDuplicateLength
        self.treeBackend = treeBackend

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

        # retrieve fingerprints with spans, sorted by spans
        spansAndFingerprints = self.fingerprintBuilder.buildFingerprints(docText)

        duplicates = []
        for previousDoc in self._docsById.values():
            docDuplicates = _buildDuplicates(
                spansAndFingerprints,
                sourceDoc=previousDoc,
                minDuplicateLength=self.minDuplicateLength,
            )
            docDuplicates = _removeOverlappingDuplicates(
                docDuplicates, self.minDuplicateLength, self.treeBackend
            )
            duplicates += docDuplicates

        # pre-compute spans that are part of duplicates
        indicesOfDuplicatesSpans = _findSpansBelongingToDuplicates(
            [s for s, _ in spansAndFingerprints], duplicates, self.treeBackend
        )
        # transform list of spans and fingerprints to mapping of fingerprints to
        # spans
        spansByFingerprint = {}
        for i, (span, fingerprint) in enumerate(spansAndFingerprints):
            # if the span belong to a duplicate we ignore it,
            # because we are only interested in recreating the duplication link
            # to the "source-most" initial document
            if i in indicesOfDuplicatesSpans:
                continue

            spansByFingerprint.setdefault(fingerprint, []).append(span)

        doc = _Document(docId, spansByFingerprint)
        self._docsById[doc.id] = doc
        return duplicates


def _buildDuplicates(targetSpansAndFingerprints, sourceDoc, minDuplicateLength):
    """
    Create a list of `Duplicate` objects, by finding and merging all consecutive
    pairs of spans with common fingerprints in source and target docs. This
    part is often the one that takes the most of the computing time.

    In simple cases, this will yield a list of non-overlapping non-contiguous
    Duplicates, that could directly be returned. Overlapping duplicates will
    only occur in more complex cases, where a copy/pasted part of the target
    text could have several potential source spans in the source text.

    Note that the extending/merging mechanic here cannot be done by an interval
    tree, because we need to merge elements that overlap in 2 dimensions (the
    source dimension and the target dimension), not just one. So maybe we would
    need some sort of 2D dimension tree. But even with a 2D dimension tree we
    have the additional condition that the result of the merge would have to
    have the same length in both dimensions so it is not clear how that would be
    handled.

    The algorithm can be roughly described like this:
    - create an empty list of "in-progress" duplicates
    - for each target span:
        - for each source spans with the same fingerprint as the target span
            - for each "in-progress" duplicate:
                - if the source and target span are consecutive to the
                  duplicate's span, extend the duplicate with these spans
        - for each "in-progress" duplicate that was not extended:
            - store it, because it means the duplicate has reach its max
              possible length. it was not extended by the last target span so it
              won't be extended by the following spans, since the target spans
              are sorted.
        - for each source span that was not merged into an existing duplicate:
            - create a new "in-progress" duplicate with it, because it
              represents a new duplication (not the continuation of an existing
              one)

    Parameters
    ----------
    targetSpansAndFingerprints: List[Tuple[Span, str]]
        List of fingerprints and corresponding spans in target document.
        Must be sorted by ascending spans
    sourceDoc: Document
        Document to be used as source
    minDuplicateLength: int
        Minimum number of characters in duplicates

    Returns
    -------
    List[Duplicate]
        List of duplicates representing spans with common text in source and
        target docs
    """

    # duplicates being built, maybe be extended by upcoming spans.
    # there will be several duplicates being built simultaneously if we
    # encounter several source spans for one target span
    inProgressDuplicates = []
    # final duplicates that will be returned
    finalDuplicates = []

    # process each span in target doc (must be sorted)
    for targetSpan, fingerprint in targetSpansAndFingerprints:
        # get corresponding spans (ie with same fingerprint) in source doc
        sourceSpans = sourceDoc.spansByFingerprint.get(fingerprint)
        if not sourceSpans:
            continue

        extendedDuplicates = []
        indicesOfMergedSourceSpans = set()

        # for each "in-progress" duplicate, try to extend it with the target
        # span and each source span
        for duplicate in inProgressDuplicates:
            extended = False
            for i, sourceSpan in enumerate(sourceSpans):
                # source and target spans should have the same length since they
                # refer to the same fingerprint
                assert sourceSpan.length == targetSpan.length

                # only spans that are "monotonic extensions" of the duplicate's
                # spans (both in source and target), ie that are contiguous or
                # overlapping but also do not start before, can be used to
                # extend the duplicate

                # target spans are sorted so we already know the new target span
                # does not start before the duplicate's target span. we just
                # need to check if it starts within or right after the
                # duplicate's target pan
                assert (
                    targetSpan.start > duplicate.targetSpan.start
                    or targetSpan.start == duplicate.targetSpan.start
                    and targetSpan.end > duplicate.targetSpan.end
                )
                if targetSpan.start > duplicate.targetSpan.end:
                    continue

                # at the outermost level, we don't iterate over sorted source
                # spans so in theory we would need to do more checks. in
                # particular, we must be careful to avoid merging 2 source spans
                # that overlap with each other but in a different way that the
                # target span , as this would create a Duplicate with different
                # source and target lengths.
                # (this can happen because source spans are not sorted, cf tests
                # cases 17_consecutive_reuse.json and 18_consecutive reuse.json)

                # in practise, just checking if extended source and target spans
                # have the same length seems to be enough and is more efficient
                # that doing preliminary checks
                extendedTargetLength = targetSpan.end - duplicate.targetSpan.start
                extendedSourceLength = sourceSpan.end - duplicate.sourceSpan.start
                if extendedSourceLength != extendedTargetLength:
                    continue

                extendedTargetSpan = Span(
                    duplicate.targetSpan.start,
                    targetSpan.end,
                    length=extendedTargetLength,
                )
                extendedSourceSpan = Span(
                    duplicate.sourceSpan.start,
                    sourceSpan.end,
                    length=extendedSourceLength,
                )

                # build and store new extended duplicate
                # (we can't modify the existing instance because the same
                # duplicate could be extended several times when there are
                # several source spans for one target span)
                extendedDuplicate = Duplicate(
                    sourceDoc.id, extendedSourceSpan, extendedTargetSpan
                )
                extendedDuplicates.append(extendedDuplicate)

                # remember this duplicate was extended
                extended = True
                # remember this source span has been used to extend a
                # pre-existing duplicate (we don't need to create a new
                # duplicate for it later)
                indicesOfMergedSourceSpans.add(i)

            # "in-progress" duplicate has not been extended. Since target spans
            # are sorted, we know it won't be extended by upcoming spans so we
            # can move it to the "final" list
            if not extended:
                # only keep if min length criteria is satisfied
                if duplicate.length >= minDuplicateLength:
                    finalDuplicates.append(duplicate)

        # only extended duplicated are kept in the new set of "in-progress"
        # duplicates
        inProgressDuplicates = extendedDuplicates

        # for source spans that have not been used to extend previously
        # existing duplicates, new duplicates must be created
        inProgressDuplicates.extend(
            Duplicate(sourceDoc.id, sourceSpan, targetSpan)
            for i, sourceSpan in enumerate(sourceSpans)
            if i not in indicesOfMergedSourceSpans
        )

    # don't forget to add remaining "in-progress" duplicates
    finalDuplicates.extend(
        duplicate
        for duplicate in inProgressDuplicates
        # only keep if min length criteria is satisfied
        if duplicate.length >= minDuplicateLength
    )

    return finalDuplicates


def _removeOverlappingDuplicates(duplicates, minDuplicateLength, treeBackend):
    """
    Remove duplicates that have overlapping target spans.

    The goal here is to handle when some part of the target document has several
    candidates as sources in the source document.

    For instance, let's take these example texts:

        source: "Hello Alice, how are you? Hello Frank, how are you?"
        target: "Hello Frank, what's up?"

    Here, the "Hello" in the target text could have been copy/pasted from the
    1st sentence of the source as well as from the 2d. The duplicate
    representing the 1st possibility will be something like this:

        Duplicate(source_start=0, source_end=4, target_start=0, target_end=4)

    while the duplicate for the 2d possibility will be

        Duplicate(source_start=25, source_end=36, target_start=0, target_end=11)

    These 2 duplicates have target spans that overlap with each other. In fact,
    the target span of 1st duplicate is fully contained in the target span of
    the 2d. Here the best duplicate is obviously the 2d because it captures a
    longer chunk of text. So when several duplicates fully overlap, we just keep
    the longest and drop the other.

    More complicated cases can occur, for instance with these texts:

        source: "Hello Frank, what's up, what's up, how are you?"
        target: "Hello Frank, what's up, how are you?"

    Here we have 2 copy/paste possibilities that are incompatible with each
    other, which are represented by the following duplicates:

        Duplicate(source_start=0, source_end=22, target_start=0, target_end=22)
        Duplicate(source_start=24, source_end=47, target_start=13, target_end=36)

    In other words, either "Hello Frank, what's up" has been copy/pasted to the
    start of the target text, or "what's up, how are you?" has been copy/pasted
    to the end of the target text. The two duplicates overlap.

    Here again, we could keep the longest duplicate and drop the other one, but
    this isn't the best solution because them we lose the information that the
    other part was, by our standards, copy/pasted.

    A better solution is be to pick the longest one and trim the other one, so
    as to remove the overlapping part, which would give the following
    duplicates:

        Duplicate(source_start=0, source_end=22, target_start=0, target_end=11)
        Duplicate(source_start=24, source_end=47, target_start=13, target_end=3

    which is equivalent to saying that these was a 1st copy/paste of "Hello Frank"
    then another one of "what's up, how are you?".

    So the algorithm consists in these simple nested loops:
    - build a queue with all the duplicates, from longest to shortest
    - while the queue is not empty:
        - take the longest duplicate and store it
        - for each other duplicate overlapping with it:
            - trim it
            - if it is zero-length or shorter than the required min length, drop
              it (ie remove it from the queue)
        - if an overlapping duplicate was trimmed and kept, sort the queue again

    Parameters
    ----------
    duplicates: List[Duplicate]
        List of non-contiguous but possible overlapping duplicates as returned
        by `_buildDuplicates()`. The list will be mutated by the call, you
        cannot use it again after
    minDuplicateLength: int
        Minimum length of duplicates. Duplicates that become shorter than this
        after being trimmed will be dropped
    treeBackend: TreeBackend
        Backend to use for overlap trees.

    Returns
    -------
    List[Duplicate]
        Updated list of on-contiguous, non-overlapping duplicates.
    """

    if treeBackend is TreeBackend.NCLS:
        if not _HAS_NCLS:
            raise Exception(
                "NCLS tree backend requested but ncls package does not seem to be installed"
            )
        return _removeOverlappingDuplicates_NCLS(duplicates, minDuplicateLength)
    elif treeBackend is TreeBackend.INTERVAL_TREE:
        if not _HAS_INTERVAL_TREE:
            raise Exception(
                "Interval tree backend requested but intervaltree package does not seem to be installed"
            )
        return _removeOverlappingDuplicates_IntervalTree(duplicates, minDuplicateLength)
    else:
        assert treeBackend is TreeBackend.NONE
        return _removeOverlappingDuplicates_NoTree(duplicates, minDuplicateLength)


def _removeOverlappingDuplicates_NoTree(duplicates, minDuplicateLength):
    """
    Implementation of `_removeOverlappingDuplicates()` not relying on any kind
    of overlap tree
    """

    keptDuplicates = []

    # sort duplicates by length so we keep bigger duplicates and remove smaller
    # overlapping duplicates
    # (we use the duplicates list as a queue)
    duplicates.sort(key=lambda d: d.length)
    while duplicates:
        # keep biggest
        duplicate = duplicates.pop()
        keptDuplicates.append(duplicate)

        # process all other duplicates that overlap with the one we just kept
        indicesToDrop = []
        mustSort = False
        for i, otherDuplicate in enumerate(duplicates):
            # try to trim if it overlaps
            trimmedDuplicate = _trimOrDropDuplicate(
                otherDuplicate, duplicate.targetSpan, minDuplicateLength
            )
            # overlapping duplicate was dropped (became too short or empty)
            if trimmedDuplicate is None:
                # remember index to delete for later
                # (we are iterating over the list right now)
                indicesToDrop.append(i)
            # overlapping duplicate was trimmed
            # (a new instance was returned)
            elif trimmedDuplicate is not otherDuplicate:
                assert trimmedDuplicate.length < otherDuplicate.length
                # erase previous instance with new instance
                duplicates[i] = trimmedDuplicate
                # we need to sort again since a duplicate is now shorter
                mustSort = True

        # delete from queue duplicates that were dropped
        for i in reversed(indicesToDrop):
            del duplicates[i]

        # re-sort if some duplicates were trimmed
        if mustSort:
            duplicates.sort(key=lambda d: d.length)

    # restore initial ascending span order
    keptDuplicates.sort(key=lambda d: (d.targetSpan.start, d.targetSpan.end))

    return keptDuplicates


def _removeOverlappingDuplicates_IntervalTree(duplicates, minDuplicateLength):
    """
    Implementation of `_removeOverlappingDuplicates()` using a IntervalTree to
    find overlapping duplicates
    """

    # build interval tree, storing duplicate index in Interval.data
    tree = it.IntervalTree(
        it.Interval(d.targetSpan.start, d.targetSpan.end, i)
        for i, d in enumerate(duplicates)
    )

    keptDuplicates = []

    # sort duplicates by length so we keep bigger duplicates and remove smaller
    # overlapping duplicates.
    # note that we need some indirection here, we cannot directly use the
    # duplicates list as a queue because the tree contains indices that refer to
    # that list. So we use a list of indices that we can safely mutate instead
    indicesOfDuplicates = sorted(
        range(len(duplicates)),
        key=lambda i: duplicates[i].length,
    )
    while indicesOfDuplicates:
        # keep biggest
        i = indicesOfDuplicates.pop()
        duplicate = duplicates[i]
        keptDuplicates.append(duplicate)

        # process all other duplicates that overlap with the one we just kept
        mustSort = False
        indicesToDrop = set()
        for interval in tree.overlap(
            duplicate.targetSpan.start, duplicate.targetSpan.end
        ):
            otherI = interval.data
            # skip when encountering original duplicate (overlaps with itself)
            if otherI == i:
                continue

            # trim or drop overlapping duplicate
            overlappingDuplicate = duplicates[otherI]
            trimmedDuplicate = _trimOrDropDuplicate(
                overlappingDuplicate, duplicate.targetSpan, minDuplicateLength
            )
            # overlapping duplicate was dropped (became too short or empty)
            if trimmedDuplicate is None:
                # remember index to delete for later
                # (we are iterating over indicesOfDuplicates right now)
                indicesToDrop.add(otherI)
                # update interval tree
                tree.remove(interval)
            # overlapping duplicate was trimmed
            else:
                # here _trimOrDropDuplicate() should always return None or a new
                # instance, not the original instance untouched, because we know
                # it overlaps
                assert trimmedDuplicate.length < overlappingDuplicate.length
                # erase previous instance with new instance
                duplicates[otherI] = trimmedDuplicate
                # we need to sort again since a duplicate is now shorter
                mustSort = True
                # update interval tree (remove previous interval, add new)
                tree.remove(interval)
                tree[
                    trimmedDuplicate.targetSpan.start : trimmedDuplicate.targetSpan.end
                ] = otherI

        # delete from queue duplicates that were dropped
        if indicesToDrop:
            indicesOfDuplicates = [
                i for i in indicesOfDuplicates if i not in indicesToDrop
            ]

        # re-sort if some duplicate were trimmed
        if mustSort:
            indicesOfDuplicates.sort(key=lambda i: duplicates[i].length)

    # restore initial sorting
    keptDuplicates.sort(key=lambda d: (d.targetSpan.start, d.targetSpan.end))

    return keptDuplicates


def _removeOverlappingDuplicates_NCLS(duplicates, minDuplicateLength):
    """
    Implementation of `_removeOverlappingDuplicates()` using NCLS to
    find overlapping duplicates
    """

    # build tree, storing duplicate index
    starts = np.array([d.targetSpan.start for d in duplicates], dtype=np.int64)
    ends = np.array([d.targetSpan.end for d in duplicates], dtype=np.int64)
    indices = np.arange(len(duplicates), dtype=np.int64)
    tree = NCLS(starts, ends, indices)

    keptDuplicates = []

    # sort duplicates by length so we keep bigger duplicates and remove smaller
    # overlapping duplicates.
    # note that we need some indirection here, we cannot directly use the
    # duplicates list as a queue because the tree contains indices that refer to
    # that list. So we use a list of indices that we can safely mutate instead
    indicesOfDuplicates = sorted(
        range(len(duplicates)),
        key=lambda i: duplicates[i].length,
    )

    while indicesOfDuplicates:
        # keep biggest
        i = indicesOfDuplicates.pop()
        duplicate = duplicates[i]
        keptDuplicates.append(duplicate)

        # process all other duplicates that overlap with the one we just kept
        mustSort = False
        indicesToDrop = set()
        for _, _, otherI in tree.find_overlap(
            duplicate.targetSpan.start, duplicate.targetSpan.end
        ):
            # skip when encountering original duplicate (overlaps with itself)
            if otherI == i:
                continue

            # trim or drop overlapping duplicate
            overlappingDuplicate = duplicates[otherI]
            trimmedDuplicate = _trimOrDropDuplicate(
                overlappingDuplicate, duplicate.targetSpan, minDuplicateLength
            )
            # overlapping duplicate was dropped (became too short or empty)
            if trimmedDuplicate is None:
                # remember index to delete for later
                # (we are iterating over indicesOfDuplicates right now)
                indicesToDrop.add(otherI)
            # overlapping duplicate was trimmed
            # (a new instance was returned)
            elif trimmedDuplicate is not overlappingDuplicate:
                assert trimmedDuplicate.length < overlappingDuplicate.length
                # erase previous instance with new instance
                duplicates[otherI] = trimmedDuplicate
                # we need to sort again since a duplicate is now shorter
                mustSort = True

        # delete from queue duplicates that were dropped
        if indicesToDrop:
            indicesOfDuplicates = [
                i for i in indicesOfDuplicates if i not in indicesToDrop
            ]

        # re-sort if some duplicate were trimmed
        if mustSort:
            indicesOfDuplicates.sort(key=lambda i: duplicates[i].length)

    # restore initial sorting
    keptDuplicates.sort(key=lambda d: (d.targetSpan.start, d.targetSpan.end))

    return keptDuplicates


def _trimOrDropDuplicate(duplicate, targetSpanToTrim, minDuplicateLength):
    """
    Trim a duplicate if its target span overlaps with `targetSpanToTrim`, or
    directly drop it if the resulting duplicate would be shorted than
    `minDuplicateLength`.

    Dropping means returning `None` instead of a duplicate.

    Both the source spans and target spans will be trimmed by the same amount.

    Parameters
    ----------
    duplicate: Duplicate
        The duplicate to trim
    targetSpanToTrim: Span
        The span that must be "trimmed-out" (ie removed) from `duplicate`
    minDuplicateLength: int
        Minimum length of duplicates

    Returns
    -------
    Optional[Duplicate]
        The trimmed duplicate. It will be the original instance left untouched
        if the duplicate's target span did not overlap with `targetSpanToTrim`,
        a new instance it it did overlap, or `None` if the trimmed duplicated
        would have been too short or empty.
    """

    trimStart = targetSpanToTrim.start
    trimEnd = targetSpanToTrim.end

    # duplicate is fully contained in span to trim, drop it
    if duplicate.targetSpan.start >= trimStart and duplicate.targetSpan.end <= trimEnd:
        return None

    # duplicate overlaps on its right-hand side
    if trimStart < duplicate.targetSpan.end < trimEnd:
        trimmedLength = trimStart - duplicate.targetSpan.start
        # drop if new length is too short
        if trimmedLength < minDuplicateLength:
            return None
        # return new duplicate with trimmed spans
        targetSpan = Span(
            duplicate.targetSpan.start,
            trimStart,
            length=trimmedLength,
        )
        sourceSpan = Span(
            duplicate.sourceSpan.start,
            duplicate.sourceSpan.start + trimmedLength,
            length=trimmedLength,
        )
        return Duplicate(duplicate.sourceDocId, sourceSpan, targetSpan)

    # duplicate overlaps on its left-hand side
    if trimStart < duplicate.targetSpan.start < trimEnd:
        trimmedLength = duplicate.targetSpan.end - trimEnd
        # drop if new length is too short
        if trimmedLength < minDuplicateLength:
            return None
        # return new duplicate with trimmed spans
        targetSpan = Span(
            trimEnd,
            duplicate.targetSpan.end,
            length=trimmedLength,
        )
        sourceSpan = Span(
            duplicate.sourceSpan.end - trimmedLength,
            duplicate.sourceSpan.end,
            length=trimmedLength,
        )
        return Duplicate(duplicate.sourceDocId, sourceSpan, targetSpan)

    # duplicate does not overlap, return as-is
    return duplicate


def _findSpansBelongingToDuplicates(spans, duplicates, treeBackend):
    """
    Identify which spans are part of duplicated areas.

    This is useful to "blacklist" the spans and corresponding fingerprints of a
    document that has just been processed, and that is going to serve as a
    potential "source" document of upcoming new documents. This is a to always
    identify duplicates to the "source-most" original document when some parts
    are copy/pasted from document to document consecutively.

    This might also speed up the processing of next documents by reducing the
    number of potential source spans.

    Parameters
    ----------
    spans: List[Span]
        List of spans of a document, as returned by a fingerprint builder
    duplicates: List[Duplicate]
        List of duplicates of the same document
    treeBackend: TreeBackend
        Backend to use for overlap trees.

    Returns
    -------
    Set[int]
        Indices of spans that overlap (even partly) with a duplicate
    """

    if treeBackend is TreeBackend.NCLS:
        if not _HAS_NCLS:
            raise Exception(
                "NCLS tree backend requested but ncls package does not seem to be installed"
            )
        return _findSpansBelongingToDuplicates_NCLS(spans, duplicates)
    elif treeBackend is TreeBackend.INTERVAL_TREE:
        if not _HAS_INTERVAL_TREE:
            raise Exception(
                "Interval tree backend requested but intervaltree package does not seem to be installed"
            )
        return _findSpansBelongingToDuplicates_IntervalTree(spans, duplicates)
    else:
        assert treeBackend is TreeBackend.NONE
        return _findSpansBelongingToDuplicates_NoTree(spans, duplicates)


def _findSpansBelongingToDuplicates_NoTree(spans, duplicates):
    """Loop-based implementation of `_findSpansBelongingToDuplicates()`"""

    return {
        i
        for i, span in enumerate(spans)
        for duplicate in duplicates
        if (
            span.start < duplicate.targetSpan.end
            and duplicate.targetSpan.start < span.end
        )
    }


def _findSpansBelongingToDuplicates_IntervalTree(spans, duplicates):
    """IntervalTree implementation of `_findSpansBelongingToDuplicates()`"""

    tree = it.IntervalTree(
        it.Interval(d.targetSpan.start, d.targetSpan.end) for d in duplicates
    )
    indicesOfDuplicatesSpans = {
        i for i, s in enumerate(spans) if tree.overlaps(s.start, s.end)
    }
    return indicesOfDuplicatesSpans


def _findSpansBelongingToDuplicates_NCLS(spans, duplicates):
    """NCLS implementation of `_findSpansBelongingToDuplicates()`"""

    # we get the answer for all spans in one shot, in one big request

    duplicateStarts = np.array([d.targetSpan.start for d in duplicates], dtype=np.int64)
    duplicateEnds = np.array([d.targetSpan.end for d in duplicates], dtype=np.int64)
    duplicateIndices = np.arange(0, len(duplicates), dtype=np.int64)
    tree = NCLS(duplicateStarts, duplicateEnds, duplicateIndices)

    spanStarts = np.array([s.start for s in spans], dtype=np.int64)
    spanEnds = np.array([s.end for s in spans], dtype=np.int64)
    spanIndices = np.arange(0, len(spans), dtype=np.int64)

    indicesOfDuplicatesSpans = tree.has_overlaps(spanStarts, spanEnds, spanIndices)
    indicesOfDuplicatesSpans = set(indicesOfDuplicatesSpans)
    return indicesOfDuplicatesSpans
