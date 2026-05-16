from django.contrib import admin
from django.utils.html import format_html

from .models import Category, Product, ProductImage


admin.site.site_header = "إدارة Kh Resin Art"
admin.site.site_title = "Kh Resin Art"
admin.site.index_title = "لوحة إدارة المنتجات"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "order")
    list_editable = ("is_active", "order")
    search_fields = ("name",)
    fields = (
        "name",
        "description",
        "is_active",
        "order",
    )

    def has_delete_permission(self, request, obj=None):
        # منع الحذف بالغلط، خصوصًا لحساب الزبونة
        if request.user.is_superuser:
            return True
        return False


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "image_preview",
        "name",
        "category",
        "is_active",
        "is_featured",
        "order",
    )

    list_editable = ("is_active", "is_featured", "order")
    list_filter = ("category", "is_active", "is_featured")
    search_fields = ("name", "short_description")
    readonly_fields = ("display_preview",)

    fieldsets = (
        ("بيانات المنتج", {
            "fields": (
                "name",
                "category",
                "short_description",
            )
        }),
        ("صورة المنتج", {
            "fields": (
                "main_image",
                "display_preview",
            ),
            "description": "ارفعي صورة المنتج الأصلية، والنظام سيجهز نسخة موحدة للعرض بعد الحفظ."
        }),
        ("إعدادات الظهور", {
            "fields": (
                "is_active",
                "is_featured",
                "order",
            )
        }),
    )

    def image_preview(self, obj):
        image = obj.display_image or obj.main_image
        if image:
            return format_html(
                '<img src="{}" style="width:70px;height:70px;object-fit:contain;border-radius:12px;background:#f7efe3;padding:4px;" />',
                image.url,
            )
        return "لا توجد صورة"

    image_preview.short_description = "الصورة"

    def display_preview(self, obj):
        if obj.display_image:
            return format_html(
                '<img src="{}" style="max-width:260px;max-height:260px;object-fit:contain;border-radius:16px;background:#f7efe3;padding:10px;" />',
                obj.display_image.url,
            )
        return "ستظهر المعاينة بعد حفظ المنتج."

    display_preview.short_description = "معاينة الصورة"

    def has_delete_permission(self, request, obj=None):
        # منع حذف المنتجات بالغلط من حساب الزبونة
        if request.user.is_superuser:
            return True
        return False