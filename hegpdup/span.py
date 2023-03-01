class Span:
    __slots__ = "start", "end", "length"

    def __init__(self, start, end, length=None):
        assert length is None or length == end - start

        self.start = start
        self.end = end
        self.length = end - start if length is None else length

    def __repr__(self):
        return f"Span(start={self.start}, end={self.end})"
