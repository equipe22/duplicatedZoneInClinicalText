class Span:
    __slots__ = "start", "end", "length"

    def __init__(self, start, end):
        self.start = start
        self.end = end
        self.length = end - start

    def __repr__(self):
        return f"Span(start={self.start}, end={self.end})"
