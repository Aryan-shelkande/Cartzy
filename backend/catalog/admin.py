from django.contrib import admin

from .models import City, Category, Location, Platform, PlatformCharges, Product, ProductPrice, ShoppingList

admin.site.register([City, Category, ShoppingList])


@admin.register(PlatformCharges)
class PlatformChargesAdmin(admin.ModelAdmin):
    list_display = [
        "platform", "location", "delivery_fee", "free_delivery_above", "handling_fee",
        "platform_fee", "small_cart_fee", "discount_percent", "source",
    ]
    list_editable = ["delivery_fee", "free_delivery_above", "handling_fee", "platform_fee", "small_cart_fee", "discount_percent"]
    list_filter = ["platform", "location", "source"]


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ["name", "city", "slug", "pincode"]


@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "logo_url", "is_active", "sort_order"]
    list_editable = ["is_active", "sort_order"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["sku", "name", "brand", "match_key", "category", "quantity", "mrp", "is_featured"]
    list_filter = ["category", "is_featured"]
    search_fields = ["sku", "name", "brand", "generic_name"]


@admin.register(ProductPrice)
class ProductPriceAdmin(admin.ModelAdmin):
    list_display = ["product", "platform", "location", "price", "is_available", "source", "updated_at"]
    list_filter = ["platform", "location", "is_available", "source"]
    search_fields = ["product__name", "product__sku"]
