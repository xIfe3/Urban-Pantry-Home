from django.contrib import admin
from django.utils.html import format_html

from .models import Category, EmailTemplate, Order, OrderItem, Product, WishlistItem


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'description')
    ordering = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('admin_thumbnail', 'name', 'price', 'stock_quantity', 'stock_status', 'category', 'is_featured', 'created_at')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'description')
    list_filter = ('category', 'is_featured', 'stock_quantity')
    list_editable = ('is_featured',)
    list_select_related = ('category',)
    date_hierarchy = 'created_at'
    ordering = ('-is_featured', '-created_at')

    @admin.display(description='Image')
    def admin_thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="44" height="44" style="object-fit:cover;border-radius:6px;" />', obj.image.url)
        return format_html('<span style="color:#829ab1;">{}</span>', 'No image')

    @admin.display(description='Stock', ordering='stock_quantity')
    def stock_status(self, obj):
        color = '#0f766e' if obj.stock_quantity > 0 else '#c53030'
        label = 'In stock' if obj.stock_quantity > 0 else 'Out of stock'
        return format_html('<strong style="color:{};">{} · {}</strong>', color, obj.stock_quantity, label)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_name', 'email', 'payment_method', 'payment_status', 'inventory_reduced', 'confirmation_sent', 'created_at')
    search_fields = ('customer_name', 'email', 'address')
    list_filter = ('payment_method', 'payment_status', 'created_at')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    readonly_fields = ('payment_reference', 'inventory_reduced', 'confirmation_sent', 'created_at')
    inlines = [OrderItemInline]


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')
    search_fields = ('user__username', 'product__name')
    list_select_related = ('user', 'product')
    ordering = ('-created_at',)


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('key', 'subject', 'enabled', 'updated_at')
    list_editable = ('enabled',)
    search_fields = ('key', 'subject', 'body')
    readonly_fields = ('updated_at',)
    fieldsets = (
        ('Template', {'fields': ('key', 'enabled', 'subject', 'body')}),
        ('Available placeholders', {'description': 'Use {{ customer_name }}, {{ order_id }}, {{ total }}, and {{ items }} in the subject or body.', 'fields': ()}),
        ('Metadata', {'fields': ('updated_at',)}),
    )
