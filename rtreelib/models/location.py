from typing import Union, Tuple, List
from functools import partial
from .rect import Rect
from .point import Point


Location = Union[
    Point,
    Rect,
    Tuple[float, float],
    Tuple[float, float, float, float],
    List[float]
]


def get_loc_intersection_fn(loc: Location):
    if isinstance(loc, Point):
        return partial(point_intersects_rect, loc)
    if isinstance(loc, Rect):
        return partial(rect_intersects_rect, loc)
    if isinstance(loc, (list, tuple)):
        if len(loc) == 2:
            point = Point(loc[0], loc[1])
            return partial(point_intersects_rect, point)
        if len(loc) == 4:
            rect = Rect(loc[0], loc[1], loc[2], loc[3])
            return partial(rect_intersects_rect, rect)
        raise TypeError(f"Invalid number of coordinates in location: {len(loc)}. Location must have either 2 "
                        f"coordinates for a Point, or 4 coordinates for a Rect.")
    raise TypeError(f"Invalid location type: {type(loc)}. Location must either be a Point, Rect, list or tuple.")


def point_intersects_rect(point: Point, rect: Rect):
    return (rect.min_x <= point.x <= rect.max_x) and (rect.min_y <= point.y <= rect.max_y)


def rect_intersects_rect(rect1: Rect, rect2: Rect):
    return rect1.intersects(rect2)
