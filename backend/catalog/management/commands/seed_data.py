from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from catalog.models import Category, City, Location, Platform, PlatformCharges, Product, ProductPrice
from catalog.seed.catalog_data import CATEGORIES, CITIES, PLATFORMS, PRODUCT_IMAGES, PRODUCTS
from catalog.seed.mock_prices import generate_mock_charges, generate_mock_prices


def match_key(generic_name, pack_size):
    """Products with the same generic name and pack size are brand alternatives."""
    return slugify(f"{generic_name} {pack_size}")


class Command(BaseCommand):
    help = "Load the demo catalogue and (re)generate mock prices and charges. Safe to run repeatedly."

    @transaction.atomic
    def handle(self, *args, **options):
        for city_name, locations in CITIES.items():
            city, _ = City.objects.get_or_create(name=city_name)
            for name, slug, pincode in locations:
                Location.objects.update_or_create(
                    slug=slug, defaults={"city": city, "name": name, "pincode": pincode}
                )

        for order, (name, slug, color, eta, logo) in enumerate(PLATFORMS):
            Platform.objects.update_or_create(
                slug=slug,
                defaults={"name": name, "color": color, "delivery_eta": eta, "logo_url": logo, "sort_order": order},
            )

        categories = {}
        for order, (name, slug, icon) in enumerate(CATEGORIES):
            categories[slug], _ = Category.objects.update_or_create(
                slug=slug, defaults={"name": name, "icon": icon, "sort_order": order}
            )

        for sku, name, brand, generic, cat, qty, mrp, emoji, featured, popularity in PRODUCTS:
            Product.objects.update_or_create(
                sku=sku,
                defaults={
                    "name": name, "brand": brand, "generic_name": generic,
                    "match_key": match_key(generic, qty), "category": categories[cat],
                    "quantity": qty, "mrp": mrp, "emoji": emoji, "image_url": PRODUCT_IMAGES.get(sku, ""),
                    "is_featured": featured, "popularity": popularity,
                },
            )

        ProductPrice.objects.filter(source=ProductPrice.SOURCE_MOCK).delete()
        prices = generate_mock_prices(
            Product.objects.all(), Platform.objects.all(), Location.objects.all()
        )
        ProductPrice.objects.bulk_create(prices)

        PlatformCharges.objects.filter(source=ProductPrice.SOURCE_MOCK).delete()
        charges = generate_mock_charges(Platform.objects.all(), Location.objects.all())
        PlatformCharges.objects.bulk_create(charges)

        available = sum(p.is_available for p in prices)
        self.stdout.write(self.style.SUCCESS(
            f"Seeded {Product.objects.count()} products, {Platform.objects.count()} platforms, "
            f"{Location.objects.count()} locations, {len(prices)} mock prices "
            f"({available} available), {len(charges)} mock charge profiles."
        ))
