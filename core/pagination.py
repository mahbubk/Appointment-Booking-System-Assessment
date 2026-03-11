"""
Purpose for give paginated result.

"""
import math
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class EnvelopePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 200

    def get_paginated_response(self, data):
        total_count = self.page.paginator.count
        page_size = self.get_page_size(self.request)
        total_pages = math.ceil(total_count / page_size) if page_size else 1

        return Response({
            "data": data,
            "errors": [],
            "meta": {
                "page": self.page.number,
                "total_pages": total_pages,
                "total_count": total_count,
            },
        })