from decimal import Decimal

from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    stock_quantity = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    image_url = models.URLField(blank=True)
    is_featured = models.BooleanField(default=False)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def is_in_stock(self):
        return self.stock_quantity > 0


class CartItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1)

    def subtotal(self):
        return self.product.price * self.quantity


class Order(models.Model):
    customer_name = models.CharField(max_length=200)
    email = models.EmailField()
    address = models.TextField()
    payment_method = models.CharField(max_length=50, default='cash')
    payment_status = models.CharField(max_length=20, default='pending')
    payment_reference = models.CharField(max_length=100, blank=True, unique=True, null=True)
    inventory_reduced = models.BooleanField(default=False)
    confirmation_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def total(self):
        return sum(item.subtotal() for item in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    def subtotal(self):
        return self.price * self.quantity


class WishlistItem(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='wishlist_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlist_items')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')


class EmailTemplate(models.Model):
    key = models.CharField(max_length=80, unique=True)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.key
