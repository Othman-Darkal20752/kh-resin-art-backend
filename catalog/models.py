import os
from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from django.db import models
from django.utils.text import slugify
from PIL import Image, ImageOps, ImageFilter


def upload_product_original(instance, filename):
    return f"products/original/{filename}"


def upload_product_display(instance, filename):
    return f"products/display/{filename}"


def reset_file_pointer(file_obj):
    """
    Reset uploaded file pointer so the same file can be processed by PIL/rembg
    and then uploaded by the configured Django storage backend.
    """
    try:
        file_obj.seek(0)
    except Exception:
        pass


_REMBG_SESSION = None


def ai_image_processing_enabled():
    """
    Enable rembg only when explicitly requested.
    Keep this disabled on Render Free to avoid Gunicorn timeout/OOM.
    Accepted true values: true, 1, yes, on.
    """
    return os.getenv("ENABLE_AI_IMAGE_PROCESSING", "False").strip().lower() in {
        "true",
        "1",
        "yes",
        "on",
    }


def get_rembg_session():
    """
    Create rembg session once per running server process.
    This function is called only when ENABLE_AI_IMAGE_PROCESSING=True.
    """
    global _REMBG_SESSION

    if _REMBG_SESSION is None:
        from rembg import new_session

        model_name = os.getenv("REMBG_MODEL", "u2netp")
        _REMBG_SESSION = new_session(model_name)

    return _REMBG_SESSION


def remove_background_safely(img):
    """
    Remove background only when AI processing is enabled.
    When disabled, return the original RGBA image so product saving stays fast and stable.
    """
    if not ai_image_processing_enabled():
        return img.convert("RGBA")

    try:
        from rembg import remove

        # Reduce image before rembg to lower CPU/RAM usage.
        ai_img = img.copy()
        ai_img.thumbnail((900, 900), Image.Resampling.LANCZOS)

        output = remove(ai_img, session=get_rembg_session())

        if isinstance(output, Image.Image):
            return output.convert("RGBA")

        return Image.open(BytesIO(output)).convert("RGBA")

    except Exception as exc:
        print(f"[image-processing] rembg failed, fallback to original image: {exc}")
        return img.convert("RGBA")


def has_transparency(img):
    try:
        alpha = img.getchannel("A")
        return alpha.getextrema()[0] < 255
    except Exception:
        return False


def make_display_image(uploaded_file, filename, size=(1200, 1200)):
    """
    Creates a clean square product image:
    - optionally removes background using rembg if ENABLE_AI_IMAGE_PROCESSING=True
    - places product on a fixed warm background
    - centers product
    - adds consistent padding
    - adds subtle shadow only if the image has transparency
    - exports WebP
    """
    background_color = (247, 239, 227, 255)  # warm beige: #F7EFE3
    padding = 120

    reset_file_pointer(uploaded_file)

    img = Image.open(uploaded_file)
    img = ImageOps.exif_transpose(img).convert("RGBA")

    # AI background removal is disabled by default on Render Free.
    img = remove_background_safely(img)

    # Crop transparent empty space around product if AI/transparent PNG produced it.
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)

    transparent_result = has_transparency(img)

    # Resize product without cropping.
    max_w = size[0] - padding * 2
    max_h = size[1] - padding * 2
    img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)

    canvas = Image.new("RGBA", size, background_color)

    x = (size[0] - img.width) // 2
    y = (size[1] - img.height) // 2

    # Add soft shadow only when image has transparency.
    if transparent_result:
        alpha = img.getchannel("A")
        shadow = Image.new("RGBA", img.size, (0, 0, 0, 70))
        shadow.putalpha(alpha.filter(ImageFilter.GaussianBlur(18)))
        canvas.alpha_composite(shadow, (x + 14, y + 20))

    canvas.alpha_composite(img, (x, y))

    output = BytesIO()
    canvas.convert("RGB").save(output, format="WEBP", quality=88, method=6)

    # Important: reset original file so Cloudinary receives it correctly.
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
            # Arabic slugify may be weak, so fallback is acceptable.
            self.slug = slugify(self.name, allow_unicode=True)
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
            self.slug = slugify(self.name, allow_unicode=True)

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
