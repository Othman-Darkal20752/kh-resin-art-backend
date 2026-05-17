from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from django.db import models
from django.utils.text import slugify
from PIL import Image, ImageOps


def upload_product_original(instance, filename):
    return f"products/original/{filename}"


def upload_product_display(instance, filename):
    return f"products/display/{filename}"


def reset_file_pointer(file_obj):
    """
    Reset uploaded file pointer so the same file can be processed by PIL
    and then uploaded by the configured Django storage backend.
    """
    try:
        file_obj.seek(0)
    except Exception:
        pass


def generate_unique_slug(model_class, value, instance_pk=None, fallback="item", max_length=180):
    """
    Generate a unique slug for a model.

    This allows multiple products/categories to have the same visible name,
    while keeping the slug unique in the database.
    Example:
        بورتوكليه
        بورتوكليه-2
        بورتوكليه-3
    """
    base_slug = slugify(value, allow_unicode=True) or fallback
    base_slug = base_slug.strip("-") or fallback
    base_slug = base_slug[:max_length].strip("-") or fallback

    slug = base_slug
    counter = 2

    while model_class.objects.filter(slug=slug).exclude(pk=instance_pk).exists():
        suffix = f"-{counter}"
        available_length = max_length - len(suffix)
        slug = f"{base_slug[:available_length].rstrip('-')}{suffix}"
        counter += 1

    return slug


def make_display_image(uploaded_file, filename, size=(1200, 1200)):
    """
    Creates a clean square product image:
    - fixed warm background
    - product centered
    - no cropping
    - WebP output

    Note: this does not remove the original photo background.
    It only standardizes the display image size and presentation.
    """
    background_color = (247, 239, 227, 255)  # warm beige: #F7EFE3
    padding = 120

    reset_file_pointer(uploaded_file)

    img = Image.open(uploaded_file)
    img = ImageOps.exif_transpose(img).convert("RGBA")

    max_w = size[0] - padding * 2
    max_h = size[1] - padding * 2
    img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)

    canvas = Image.new("RGBA", size, background_color)

    x = (size[0] - img.width) // 2
    y = (size[1] - img.height) // 2
    canvas.alpha_composite(img, (x, y))

    output = BytesIO()
    canvas.convert("RGB").save(output, format="WEBP", quality=88, method=6)

    # Important: PIL consumes the original uploaded file.
    # Reset it so Cloudinary receives the full original file, not an empty stream.
    reset_file_pointer(uploaded_file)

    base_name = Path(filename).stem
    return ContentFile(output.getvalue(), name=f"{base_name}_display.webp")


class Category(models.Model):
    name = models.CharField("اسم التصنيف", max_length=120)
    slug = models.SlugField("الرابط", max_length=140, unique=True, blank=True)
    description = models.TextField("وصف مختصر", blank=True)
    is_active = models.BooleanField("ظاهر بالموقع", default=True)
    order = models.PositiveIntegerField("الترتيب", default=0)

    class Meta:
        verbose_name = "تصنيف"
        verbose_name_plural = "التصنيفات"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(
                Category,
                self.name,
                instance_pk=self.pk,
                fallback="category",
                max_length=140,
            )
        else:
            self.slug = generate_unique_slug(
                Category,
                self.slug,
                instance_pk=self.pk,
                fallback="category",
                max_length=140,
            )

        super().save(*args, **kwargs)


class Product(models.Model):
    category = models.ForeignKey(
        Category,
        verbose_name="التصنيف",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )

    name = models.CharField("اسم المنتج", max_length=160)
    slug = models.SlugField("الرابط", max_length=180, unique=True, blank=True, allow_unicode=True)

    short_description = models.TextField("وصف مختصر", blank=True)

    main_image = models.ImageField(
        "الصورة الأصلية",
        upload_to=upload_product_original,
        blank=True,
        null=True,
    )

    colors_note = models.CharField(
        "الألوان",
        max_length=255,
        blank=True,
        default="",
    )

    customization_note = models.TextField(
        "التخصيص",
        blank=True,
        default="",
    )

    display_image = models.ImageField(
        "صورة العرض الموحدة",
        upload_to=upload_product_display,
        blank=True,
        null=True,
        editable=False,
    )

    is_active = models.BooleanField("ظاهر بالموقع", default=True)
    is_featured = models.BooleanField("مميز بالصفحة الرئيسية", default=False)
    order = models.PositiveIntegerField("الترتيب", default=0)

    created_at = models.DateTimeField("تاريخ الإضافة", auto_now_add=True)
    updated_at = models.DateTimeField("آخر تعديل", auto_now=True)

    class Meta:
        verbose_name = "منتج"
        verbose_name_plural = "المنتجات"
        ordering = ["order", "-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        old_image_name = None

        if self.pk:
            old = Product.objects.filter(pk=self.pk).first()
            if old and old.main_image:
                old_image_name = old.main_image.name

        current_image_name = self.main_image.name if self.main_image else None

        image_changed = bool(
            self.main_image
            and (
                not getattr(self.main_image, "_committed", True)
                or current_image_name != old_image_name
            )
        )

        if not self.slug:
            self.slug = generate_unique_slug(
                Product,
                self.name,
                instance_pk=self.pk,
                fallback="product",
                max_length=180,
            )
        else:
            self.slug = generate_unique_slug(
                Product,
                self.slug,
                instance_pk=self.pk,
                fallback="product",
                max_length=180,
            )

        if image_changed:
            self.display_image = make_display_image(
                self.main_image,
                self.main_image.name,
            )
            reset_file_pointer(self.main_image)

        super().save(*args, **kwargs)


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        verbose_name="المنتج",
        on_delete=models.CASCADE,
        related_name="gallery",
    )
    image = models.ImageField("صورة إضافية", upload_to="products/gallery/")
    alt_text = models.CharField("نص بديل", max_length=160, blank=True)
    order = models.PositiveIntegerField("الترتيب", default=0)

    class Meta:
        verbose_name = "صورة منتج"
        verbose_name_plural = "صور المنتجات"
        ordering = ["order", "id"]

    def __str__(self):
        return f"صورة - {self.product.name}"