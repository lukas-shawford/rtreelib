from typing import TypeVar, List


TRect = TypeVar('TRect', bound='Rect')


class Rect:
    def __init__(self, min_x: float, min_y: float, max_x: float, max_y: float):
        self.min_x = min_x
        self.min_y = min_y
        self.max_x = max_x
        self.max_y = max_y

    def __eq__(self, other):
        if isinstance(other, Rect):
            return self.min_x == other.min_x\
                   and self.min_y == other.min_y\
                   and self.max_x == other.max_x\
                   and self.max_y == other.max_y
        return False

    def __repr__(self):
        return f'Rect({self.min_x}, {self.min_y}, {self.max_x}, {self.max_y})'

    def union(self, rect: TRect) -> TRect:
        return Rect(
            min_x=min(self.min_x, rect.min_x),
            min_y=min(self.min_y, rect.min_y),
            max_x=max(self.max_x, rect.max_x),
            max_y=max(self.max_y, rect.max_y)
        )

    @property
    def width(self):
        return self.max_x - self.min_x

    @property
    def height(self):
        return self.max_y - self.min_y

    def area(self) -> float:
        return self.width * self.height


def union(rect1: Rect, rect2: Rect) -> Rect:
    if rect1 is None:
        return rect2
    if rect2 is None:
        return rect1
    return rect1.union(rect2)


def union_all(rects: List[Rect]) -> Rect:
    result = None
    for rect in rects:
        result = union(result, rect)
    return result
