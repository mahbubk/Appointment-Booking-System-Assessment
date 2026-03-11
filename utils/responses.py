"""
Helper method for API Response
"""

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q


def paginate_queryset(request, queryset, serializer_class):
    try:
        page = int(request.query_params.get("page", 1))
    except (ValueError, TypeError):
        page = 1

    try:
        page_size = int(request.query_params.get("page_size", 20))
        page_size = max(1, min(page_size, 200))
    except (ValueError, TypeError):
        page_size = 20

    paginator = Paginator(queryset, page_size)

    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    serializer = serializer_class(page_obj.object_list, many=True)

    return {
        "data": serializer.data,
        "errors": [],
        "meta": {
            "page": page_obj.number,
            "total_pages": paginator.num_pages,
            "total_count": paginator.count,
        },
    }


def filter_queryset(queryset, request, search_fields=None):
    search = request.query_params.get("search", "").strip()
    if search and search_fields:
        query = Q()
        for field in search_fields:
            query |= Q(**{f"{field}__icontains": search})
        queryset = queryset.filter(query)

    start_date = request.query_params.get("start_date", "").strip()
    if start_date:
        queryset = queryset.filter(start_time__date__gte=start_date)

    end_date = request.query_params.get("end_date", "").strip()
    if end_date:
        queryset = queryset.filter(start_time__date__lte=end_date)

    return queryset