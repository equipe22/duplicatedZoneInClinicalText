import re

from .span import Span

_DEFAULT_WORD_REGEXP = re.compile(r"[\w\d]+")
_NEWLINE_REGEXP = re.compile(r"[^\r\n]+")


class WordFingerprintBuilder:
    """
    Builds fingerprints for a set of text documents, for identification of
    duplicates.

    The fingerprint builder remembers previously seen documents and will reuse
    fingerprint ids for identical text chunks.
    """

    def __init__(
        self,
        fingerprintLength=2,
        orf=1,
        wordRegexp=_DEFAULT_WORD_REGEXP,
        caseSensitive=True,
        allowMultiline=True,
    ):
        """
        Parameters
        ----------
        fingerprintLength: int
            Number of words to include in each fingerprinted chunk. The
            non-words characters between the words of a chunk will also be
            included in the chunk. Must be at least 2 otherwise it is
            impossible to take into account non-word chars between words.
        orf: int
            Open Reading Frame length. Shift size used when moving the
            fingerprint window over the text (the window having a size of
            `fingerprintLength` words)
        wordRegexp: re.Pattern
            Regexp object to use to identify word boundaries in texts
        caseSensitive: bool
            Whether case should be taken into account when testing if chunks of
            text are equal
        allowMultiline: bool
            Whether fingerprints can span over multiple lines. Set to False
            to prevent multiline duplicates
        """

        if fingerprintLength < 2:
            raise ValueError("Fingerprint length must be at least 2")

        self.fingerprintLength = fingerprintLength
        self.orf = orf
        self.wordRegexp = wordRegexp
        self.caseSensitive = caseSensitive
        self.allowMultiline = allowMultiline

        # mapping giving the unique fingerprint id corresponding to a previously
        # seen chunk of text
        self._fingerprintIdByChunk = dict()

    def buildFingerprints(self, text):
        """
        Return a list of fingerprint ids and the character spans in which
        they are found in `text`.

        Parameters
        ----------
        text: str
            Text for which to build the fingerprints

        Returns
        -------
        List[Tuple[Span, int]]
            List of ids of fingerprints contained in `text` and their
            corresponding characters spans, sorted by ascending span
        """

        if not self.caseSensitive:
            text = text.lower()

        spansAndFingerprintIds = []

        if self.allowMultiline:
            return list(self._buildFingerprints(text, 0))

        # build fingerprints line by line if multiline fingerprints aren't
        # allowed
        spansAndFingerprintIds = []
        for match in _NEWLINE_REGEXP.finditer(text):
            lineStart = match.start()
            line = match.group()
            spansAndFingerprintIdsForLine = self._buildFingerprints(line, lineStart)
            spansAndFingerprintIds.extend(spansAndFingerprintIdsForLine)

        return spansAndFingerprintIds

    def _buildFingerprints(self, text, textStart=0):
        """
        Yield fingerprint ids and character spans in which they are found in
        `text`, using `textStart` to offset the spans.

        Parameters
        ----------
        text: str
            Text for which to build the fingerprints
        textStart:
            Position of `text` in the full document text if it is a line rather
            than the full text

        Returns
        -------
        Iterator[Tuple[Span, int]]
            Iterator over ids of fingerprints contained in `text` and their
            corresponding characters spans, sorted by ascending span
        """

        # get start/end boundaries of all words using regexp
        wordSpans = [match.span() for match in self.wordRegexp.finditer(text)]

        # build fingerprints for consecutive words
        nbWords = len(wordSpans)
        for i in range(0, nbWords, self.orf):
            # take start of current word
            start, _ = wordSpans[i]
            # take end of last word to include in chunk
            end_i = min(i + self.fingerprintLength, nbWords)
            _, end = wordSpans[end_i - 1]
            chunk = text[start:end]

            # find existing fingerprint id for chunk or create new id
            # if chunk is unseen
            fingerprintId = self._fingerprintIdByChunk.setdefault(
                chunk, len(self._fingerprintIdByChunk)
            )

            span = Span(textStart + start, textStart + end)
            yield span, fingerprintId

            # if we reached end of list of words, break out
            if end_i == nbWords:
                break
