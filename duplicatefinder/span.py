class Span:
    """Range of character positions in a document text"""

    __slots__ = "start", "end", "length"

    def __init__(self, start, end, length=None):
        """
        Parameters
        ----------
        start: int
            Position of the 1st character in the span (included)
        end: int
            Position of the last character of the span, excluded (ie the 1st
            char not in the span)
        length: Optional[int]
            Length of the span, if already known (to avoid recomputation)
        """

        assert end > start
        assert length is None or length == end - start

        self.start = start
        self.end = end
        self.length = end - start if length is None else length

    def __repr__(self):
        return f"Span(start={self.start}, end={self.end})"
