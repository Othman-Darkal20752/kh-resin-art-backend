from rest_framework import serializers
from .models import Category, Product, ProductImage


class ProductImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["id", "image_url", "alt_text", "order"]

    def get_image_url(self, obj):
        request = self.context.get("request")
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description", "order"]


class ProductListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_slug = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "short_description",
            "category",
            "category_name",
            "category_slug",
            "image_url",
            "is_featured",
            "order",
            "created_at",
            "updated_at",
        ]

    def get_category_slug(self, obj):
        if obj.category:
            return obj.category.slug
        return None

    def get_image_url(self, obj):
        request = self.context.get("request")
        image = obj.display_image or obj.main_image

        if image and request:
            return request.build_absolute_uri(image.url)

        return None


class ProductDetailSerializer(ProductListSerializer):
    gallery = ProductImageSerializer(many=True, read_only=True)

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + [
            "gallery",
        ]
