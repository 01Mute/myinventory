"""The queries under measurement.

Every case is built by driving the real view code rather than by hand-writing
SQL. A hand-written approximation drifts away from the application the moment
somebody edits a filter, and then the benchmark is measuring a query nobody
runs. Building the queryset through ItemViewSet means the measurement follows
the code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from django.contrib.auth import get_user_model
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from items.models import Item, ItemLocationHistory
from items.views import ItemViewSet
from locations.models import LocationNode
from locations.views import LocationNodeViewSet

User = get_user_model()

# The generator spreads item names across a fixed noun list, so this term
# matches a known, stable share of the table.
SEARCH_TERM = "드라이버"
PAGE_SIZE = 200


@dataclass(frozen=True)
class Context:
    """Concrete rows the cases are built against."""

    user: object
    room_node: LocationNode
    box_node: LocationNode
    item_id: int


@dataclass(frozen=True)
class QueryCase:
    name: str
    description: str
    build: Callable[[Context], object]
    # "list" evaluates the queryset the way a serializer would; "count" issues
    # the COUNT the paginator issues. The distinction matters because Django
    # wraps a DISTINCT queryset in a subquery to count it, producing a plan that
    # looks nothing like the page query's plan.
    mode: str = "list"


def _viewset(viewset_class, user, action, params=None, **kwargs):
    """Instantiate a viewset outside the URL router.

    DRF viewsets read self.request and self.action, and ItemViewSet in
    particular branches on action to decide whether query-parameter filters
    apply at all. Both have to be set for get_queryset() to behave the way a
    real request makes it behave.
    """
    request = Request(APIRequestFactory().get("/", params or {}))
    request.user = user

    viewset = viewset_class()
    viewset.request = request
    viewset.action = action
    viewset.kwargs = kwargs
    viewset.format_kwarg = None
    return viewset


def item_search_page(context: Context):
    viewset = _viewset(ItemViewSet, context.user, "list", {"q": SEARCH_TERM})
    return viewset.get_queryset()[:PAGE_SIZE]


def item_search_count(context: Context):
    """The COUNT half of a paginated list response.

    PageNumberPagination issues a count before it issues the page. With a
    DISTINCT over three joined tables that half is frequently the expensive one,
    and it is invisible if only the page query is measured.
    """
    viewset = _viewset(ItemViewSet, context.user, "list", {"q": SEARCH_TERM})
    return viewset.get_queryset()


def item_by_location_code(context: Context):
    viewset = _viewset(
        ItemViewSet,
        context.user,
        "list",
        {"location_code": context.room_node.full_code},
    )
    return viewset.get_queryset()[:PAGE_SIZE]


def item_by_leaf_node(context: Context):
    viewset = _viewset(
        ItemViewSet,
        context.user,
        "list",
        {"location_node_id": str(context.box_node.id)},
    )
    return viewset.get_queryset()[:PAGE_SIZE]


def item_list_unfiltered(context: Context):
    viewset = _viewset(ItemViewSet, context.user, "list")
    return viewset.get_queryset()[:PAGE_SIZE]


def item_history(context: Context):
    return (
        ItemLocationHistory.objects.filter(item_id=context.item_id)
        .select_related("from_location_node", "to_location_node", "created_by")
        .order_by("-moved_at", "-id")
    )


def location_list(context: Context):
    viewset = _viewset(LocationNodeViewSet, context.user, "list")
    return viewset.get_queryset()[:PAGE_SIZE]


def location_subtree_rows(context: Context):
    """Every node under one home, which is what tree serialisation loads.

    LocationNodeTreeSerializer was rewritten to fetch the whole set in one query
    and assemble the tree in Python. This measures the cost of that one query.
    """
    return LocationNode.objects.filter(home_id=context.room_node.home_id).order_by(
        "path", "sort_order", "id"
    )


CASES = (
    QueryCase(
        name="item_search_page",
        description="검색 ?q= 의 페이지 조회 (5중 OR icontains + 3테이블 조인 + DISTINCT)",
        build=item_search_page,
    ),
    QueryCase(
        name="item_search_count",
        description="검색 ?q= 의 총건수 조회 (페이지네이션이 함께 실행하는 절반)",
        build=item_search_count,
        mode="count",
    ),
    QueryCase(
        name="item_by_location_code",
        description="위치코드 접두 검색 ?location_code= (full_code icontains)",
        build=item_by_location_code,
    ),
    QueryCase(
        name="item_by_leaf_node",
        description="단일 위치노드의 아이템 조회 ?location_node_id=",
        build=item_by_leaf_node,
    ),
    QueryCase(
        name="item_list_unfiltered",
        description="필터 없는 아이템 목록 첫 페이지",
        build=item_list_unfiltered,
    ),
    QueryCase(
        name="item_history",
        description="아이템 1건의 이동이력 (이력 테이블 전체에서 추출)",
        build=item_history,
    ),
    QueryCase(
        name="location_list",
        description="위치노드 목록 첫 페이지",
        build=location_list,
    ),
    QueryCase(
        name="location_subtree_rows",
        description="집 1채의 전체 위치노드 (트리 직렬화가 읽는 단일 쿼리)",
        build=location_subtree_rows,
    ),
)


def build_context(username_prefix: str) -> Context:
    """Pick concrete rows for the generated dataset to measure against."""
    user = (
        User.objects.filter(username__startswith=username_prefix)
        .order_by("id")
        .first()
    )
    if user is None:
        raise LookupError(
            f"'{username_prefix}'로 시작하는 사용자가 없습니다. "
            "먼저 generate_load를 실행하세요."
        )

    room = (
        LocationNode.objects.filter(home__owner=user, level=0).order_by("id").first()
    )
    box = LocationNode.objects.filter(home__owner=user, level=3).order_by("id").first()
    item_id = (
        Item.objects.filter(owner=user).order_by("id").values_list("id", flat=True).first()
    )
    if room is None or box is None or item_id is None:
        raise LookupError(
            "측정에 쓸 위치노드나 아이템이 없습니다. 먼저 generate_load를 실행하세요."
        )

    return Context(user=user, room_node=room, box_node=box, item_id=item_id)
