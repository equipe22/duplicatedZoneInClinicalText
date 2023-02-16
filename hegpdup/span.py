class Span:
    __slots__ = "start", "end"

    def __init__(self, start, end):
        self.start = start
        self.end = end

    @property
    def length(self):
        return self.end - self.start

    def __hash__(self):
        return hash((self.start, self.end))

    def __repr__(self):
        return f"Span(start={self.start}, end={self.end})"
