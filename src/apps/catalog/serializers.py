from rest_framework import serializers
from .models import Category, Product, ProductImage, ContentBlock

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image_url', 'alt_text', 'is_primary', 'sort_order']

class ContentBlockSerializer(serializers.ModelSerializer):
    block_type_display = serializers.CharField(source='get_block_type_display', read_only=True)
    class Meta:
        model = ContentBlock
        fields = ['id', 'block_type', 'block_type_display', 'title', 'subtitle', 'content', 'extra_data', 'sort_order']

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'icon', 'sort_order']

class ProductListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    primary_image_url = serializers.SerializerMethodField()
    has_discount = serializers.BooleanField(read_only=True)
    discount_percent = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'title', 'slug', 'sku', 'category', 'category_name', 'summary', 'price', 'compare_at_price', 'has_discount', 'discount_percent', 'stock', 'is_available', 'is_featured', 'primary_image_url']

    def get_primary_image_url(self, obj):
        img = obj.primary_image
        return img.image_url if img else None

class ProductDetailSerializer(ProductListSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    content_blocks = ContentBlockSerializer(many=True, read_only=True)
    schema_json_ld = serializers.CharField(source='get_schema_json_ld', read_only=True)

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + ['meta_title', 'meta_description', 'images', 'content_blocks', 'schema_json_ld']
