import uuid

from django.core.validators import MinValueValidator
from django.db import models


class City(models.Model):
    name = models.CharField(max_length=80, unique=True)

    class Meta:
        verbose_name_plural = "cities"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Location(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="locations")
    name = models.CharField(max_length=80)
    slug = models.SlugField(unique=True)
    pincode = models.CharField(max_length=10, blank=True)

    class Meta:
        ordering = ["city__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["city", "name"], name="unique_location_per_city")
        ]

    def __str__(self):
        return f"{self.name}, {self.city}"


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=8, help_text="Emoji shown in category shortcuts")
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class Platform(models.Model):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(unique=True)
    color = models.CharField(max_length=7, help_text="Hex colour for the badge")
    logo_url = models.CharField(
        max_length=300, blank=True,
        help_text="Absolute URL or a path under the frontend's public/ folder, e.g. /logos/zepto.png",
    )
    delivery_eta = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    """A canonical product. One record per real-world SKU, shared by all platforms."""

    sku = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=150)
    brand = models.CharField(max_length=80)
    generic_name = models.CharField(max_length=80, blank=True, help_text="Brand-free name, e.g. Salt")
    match_key = models.SlugField(
        max_length=120, blank=True, db_index=True,
        help_text="Generic name + pack size. Products sharing it are brand alternatives.",
    )
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    quantity = models.CharField(max_length=40, help_text="Pack size, e.g. 500 g or 1 L")
    mrp = models.DecimalField(max_digits=8, decimal_places=2)
    image_url = models.CharField(
        max_length=300, blank=True,
        help_text="Absolute URL or a path under the frontend's public/ folder",
    )
    emoji = models.CharField(max_length=8, blank=True, help_text="Fallback visual when no image")
    is_featured = models.BooleanField(default=False)
    popularity = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.brand} {self.name} ({self.quantity})"


class ProductPrice(models.Model):
    """Price of a product on one platform at one location.

    `source` records where the price came from so mock data can later be
    replaced by a licensed feed or partner API without changing consumers.
    """

    SOURCE_MOCK = "mock"

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="prices")
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE, related_name="prices")
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="prices")
    price = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    is_available = models.BooleanField(default=True)
    source = models.CharField(max_length=30, default=SOURCE_MOCK)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "platform", "location"], name="unique_price_per_listing"
            )
        ]
        indexes = [models.Index(fields=["location", "product"])]

    def __str__(self):
        return f"{self.product.sku} @ {self.platform.slug}/{self.location.slug}: {self.price}"


class PlatformCharges(models.Model):
    """Fees and discount one platform applies to an order at one location.

    final payable = subtotal + delivery + handling + platform fee + small-cart fee - discount
    """

    platform = models.ForeignKey(Platform, on_delete=models.CASCADE, related_name="charges")
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="charges")
    delivery_fee = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    free_delivery_above = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Delivery is free when the subtotal reaches this amount. Empty = never free.",
    )
    handling_fee = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    platform_fee = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    small_cart_fee = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    small_cart_below = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, help_text="Small-cart fee applies below this subtotal."
    )
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_max = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True, help_text="Cap on the discount. Empty = no cap."
    )
    discount_min_order = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    source = models.CharField(max_length=30, default=ProductPrice.SOURCE_MOCK)

    class Meta:
        verbose_name_plural = "platform charges"
        constraints = [
            models.UniqueConstraint(fields=["platform", "location"], name="unique_charges_per_platform_location")
        ]

    def __str__(self):
        return f"{self.platform.slug}/{self.location.slug} charges"


class ShoppingList(models.Model):
    """Anonymous cart addressed by UUID. A nullable user FK can be added with auth later."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class ShoppingListItem(models.Model):
    shopping_list = models.ForeignKey(ShoppingList, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1)])
    accept_alternatives = models.BooleanField(
        default=False, help_text="Count another brand of the same item and size when this one is unavailable."
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["added_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["shopping_list", "product"], name="unique_product_per_list"
            )
        ]

    def __str__(self):
        return f"{self.quantity} x {self.product.sku}"
