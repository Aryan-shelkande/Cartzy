from rest_framework import serializers

from .models import Category, Location, Platform, Product, ShoppingList, ShoppingListItem


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "icon", "product_count"]


class LocationSerializer(serializers.ModelSerializer):
    city = serializers.CharField(source="city.name")

    class Meta:
        model = Location
        fields = ["id", "name", "slug", "city", "pincode"]


class PlatformSerializer(serializers.ModelSerializer):
    class Meta:
        model = Platform
        fields = ["id", "name", "slug", "color", "logo_url", "delivery_eta"]


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    # Filled by services.annotate_price_summary; null when not annotated or unavailable.
    min_price = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True, default=None)
    max_price = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True, default=None)
    savings = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True, default=None)
    available_count = serializers.IntegerField(read_only=True, default=None)
    # Filled by services.annotate_alternatives_count.
    alternatives_count = serializers.IntegerField(read_only=True, default=None)

    class Meta:
        model = Product
        fields = [
            "id", "sku", "name", "brand", "generic_name", "match_key", "category", "quantity", "mrp",
            "image_url", "emoji", "is_featured",
            "min_price", "max_price", "savings", "available_count", "alternatives_count",
        ]


class OfferSerializer(serializers.Serializer):
    platform = PlatformSerializer()
    price = serializers.DecimalField(max_digits=8, decimal_places=2, allow_null=True)
    is_available = serializers.BooleanField()
    is_cheapest = serializers.BooleanField()
    updated_at = serializers.DateTimeField(allow_null=True)
    source = serializers.CharField(allow_null=True)


class ProductComparisonSerializer(serializers.Serializer):
    product = ProductSerializer()
    alternatives = ProductSerializer(many=True)
    location = LocationSerializer()
    offers = OfferSerializer(many=True)
    cheapest_price = serializers.DecimalField(max_digits=8, decimal_places=2, allow_null=True)
    highest_price = serializers.DecimalField(max_digits=8, decimal_places=2, allow_null=True)
    savings = serializers.DecimalField(max_digits=8, decimal_places=2, allow_null=True)
    available_count = serializers.IntegerField()
    is_demo_data = serializers.BooleanField()


def money(**kwargs):
    return serializers.DecimalField(max_digits=10, decimal_places=2, **kwargs)


class MissingProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "brand", "quantity"]


class LineProductSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(slug_field="slug", read_only=True)

    class Meta:
        model = Product
        fields = ["id", "name", "brand", "quantity", "image_url", "emoji", "category"]


class CartLineSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField()
    status = serializers.CharField()  # exact | alternative | alternative_available | unavailable
    matched_product = LineProductSerializer(allow_null=True)
    unit_price = money(allow_null=True)
    line_total = money(allow_null=True)
    is_available = serializers.BooleanField()
    accept_alternatives = serializers.BooleanField()


class ChargesSerializer(serializers.Serializer):
    subtotal = money()
    delivery_fee = money()
    handling_fee = money()
    platform_fee = money()
    other_charges = money()
    discount = money()
    fees_total = money()
    total = money()
    free_delivery_above = money(allow_null=True)


class PlatformCartSerializer(serializers.Serializer):
    platform = PlatformSerializer()
    total = money()
    subtotal = money()
    charges = ChargesSerializer()
    is_complete = serializers.BooleanField()
    is_exact_match = serializers.BooleanField()
    would_complete_with_alternatives = serializers.BooleanField()
    is_cheapest = serializers.BooleanField()
    is_highest = serializers.BooleanField()
    extra_vs_cheapest = money(allow_null=True)
    requested_items = serializers.IntegerField()
    available_items = serializers.IntegerField()
    exact_items = serializers.IntegerField()
    alternative_items = serializers.IntegerField()
    alternative_available_items = serializers.IntegerField()
    unavailable_items = serializers.IntegerField()
    missing_products = MissingProductSerializer(many=True)
    lines = CartLineSerializer(many=True)


class CartComparisonSerializer(serializers.Serializer):
    location = LocationSerializer()
    item_count = serializers.IntegerField()
    unit_count = serializers.IntegerField()
    platforms = PlatformCartSerializer(many=True)
    complete_count = serializers.IntegerField()
    cheapest_platform = PlatformSerializer(allow_null=True)
    cheapest_total = money(allow_null=True)
    highest_platform = PlatformSerializer(allow_null=True)
    highest_total = money(allow_null=True)
    savings = money(allow_null=True)
    cheapest_exact_platform = PlatformSerializer(allow_null=True)
    cheapest_exact_total = money(allow_null=True)
    is_demo_data = serializers.BooleanField()


class BrandOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "brand", "quantity"]


class ShoppingListItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    brand_options = serializers.SerializerMethodField()

    class Meta:
        model = ShoppingListItem
        fields = ["product", "quantity", "accept_alternatives", "brand_options"]

    def get_brand_options(self, item):
        """Every brand of this item and size, the chosen one included. Uses `brand_groups` context."""
        group = self.context.get("brand_groups", {}).get(item.product.match_key) or [item.product]
        return BrandOptionSerializer(group, many=True).data


class ShoppingListSerializer(serializers.ModelSerializer):
    items = ShoppingListItemSerializer(many=True, read_only=True)

    class Meta:
        model = ShoppingList
        fields = ["id", "items", "updated_at"]


class AddItemSerializer(serializers.Serializer):
    product_id = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), source="product")
    quantity = serializers.IntegerField(min_value=1, max_value=99, default=1)


class UpdateItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1, max_value=99, required=False)
    accept_alternatives = serializers.BooleanField(required=False)
    # Switch the item to another brand of the same item and size.
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source="product", required=False
    )

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Send quantity, accept_alternatives or product_id.")
        return attrs
