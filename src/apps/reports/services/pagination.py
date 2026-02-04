from rest_framework.pagination import PageNumberPagination


class ReportPagination(PageNumberPagination):
    page_query_param = "page"          # /reports/?page=2
    page_size_query_param = "per_page" # /reports/?per_page=20
    page_size = 10
    max_page_size = 200  