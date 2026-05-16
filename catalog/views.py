from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Category, Product
from .serializers import (
    CategorySerializer,
    ProductListSerializer,
    ProductDetailSerializer,
)


class CategoryViewSet(ReadOnlyModelViewSet):
    serializer_class = CategorySerializer
    lookup_field = "slug"

    def get_queryset(self):
        return Category.objects.filter(is_active=True).order_by("order", "name")


class ProductViewSet(ReadOnlyModelViewSet):
    lookup_field = "slug"
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name", "short_description", "category__name"]
    ordering_fields = ["order", "created_at", "name"]

    def get_queryset(self):
        queryset = (
            Product.objects
            .filter(is_active=True)
            .select_related("category")
            .prefetch_related("gallery")
            .order_by("order", "-created_at")
        )

        category_slug = self.request.query_params.get("category")
        featured = self.request.query_params.get("featured")

        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        if featured == "true":
            queryset = queryset.filter(is_featured=True)

        return queryset

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ProductDetailSerializer
        return ProductListSerializer