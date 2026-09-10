from decimal import Decimal
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .admin import ProductAdmin
from .models import Category, Order, Product, WishlistItem


class EcommerceFlowTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name='Wireless Headphones',
            slug='wireless-headphones',
            price=Decimal('129.99'),
            description='Immersive audio for daily use.',
            stock_quantity=10,
            image_url='https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=600&q=80',
        )

    def test_admin_thumbnail_handles_missing_image(self):
        product = Product.objects.create(
            name='No Image Product',
            slug='no-image-product',
            price=Decimal('99.99'),
            stock_quantity=3,
        )
        admin_instance = ProductAdmin(Product, admin.site)
        rendered = admin_instance.admin_thumbnail(product)
        self.assertIn('No image', str(rendered))

    def test_home_page_uses_featured_product_for_hero(self):
        Product.objects.create(
            name='Everyday Blender',
            slug='everyday-blender',
            price=Decimal('249.00'),
            stock_quantity=5,
            is_featured=True,
        )
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['featured_product'].name, 'Everyday Blender')

    def test_home_page_shows_products(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Wireless Headphones')

    def test_cart_and_checkout_flow(self):
        add_response = self.client.post(reverse('add_to_cart', args=[self.product.slug]), {'quantity': 1})
        self.assertEqual(add_response.status_code, 302)

        cart_response = self.client.get(reverse('cart'))
        self.assertContains(cart_response, 'Wireless Headphones')
        self.assertContains(cart_response, '1')

        update_response = self.client.post(reverse('cart'), {str(self.product.id): '3'})
        self.assertEqual(update_response.status_code, 302)

        self.client.post(
            reverse('checkout'),
            {
                'customer_name': 'Ada Lovelace',
                'email': 'ada@example.com',
                'address': '123 Tech Avenue',
                'payment_method': 'cash',
            },
        )

        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(Order.objects.first().items.count(), 1)
        self.assertEqual(Order.objects.first().items.first().quantity, 3)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 7)

    def test_cannot_add_more_than_available_stock(self):
        response = self.client.post(reverse('add_to_cart', args=[self.product.slug]), {'quantity': 11})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session.get('cart', {}), {})

    @patch('store.views._paystack_request')
    def test_paystack_callback_completes_order_and_reduces_stock(self, paystack_request):
        paystack_request.side_effect = [
            {'status': True, 'data': {'authorization_url': 'https://checkout.paystack.com/test'}},
            {'status': True, 'data': {'status': 'success'}},
        ]
        self.client.post(reverse('add_to_cart', args=[self.product.slug]), {'quantity': 2})
        response = self.client.post(
            reverse('checkout'),
            {
                'customer_name': 'Ada Lovelace',
                'email': 'ada@example.com',
                'address': '123 Tech Avenue',
                'payment_method': 'paystack',
            },
        )
        self.assertEqual(response.status_code, 302)
        order = Order.objects.get()
        self.assertEqual(order.payment_status, 'pending')
        self.client.get(reverse('paystack_callback'), {'reference': order.payment_reference})
        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(order.payment_status, 'paid')
        self.assertTrue(order.inventory_reduced)
        self.assertTrue(order.confirmation_sent)
        self.assertEqual(self.product.stock_quantity, 8)

    def test_category_page_shows_products(self):
        category = Category.objects.create(name='Audio', slug='audio')
        Product.objects.create(
            name='Bluetooth Speaker',
            slug='bluetooth-speaker',
            price=Decimal('89.99'),
            description='Portable sound.',
            category=category,
        )

        response = self.client.get(reverse('category_products', args=[category.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bluetooth Speaker')

    def test_registration_creates_user(self):
        response = self.client.post(
            reverse('register'),
            {
                'username': 'newuser',
                'email': 'new@example.com',
                'password1': 'StrongPass123!',
                'password2': 'StrongPass123!',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(get_user_model().objects.filter(username='newuser').exists())

    def test_search_filters_products(self):
        Product.objects.create(
            name='Gaming Mouse',
            slug='gaming-mouse',
            price=Decimal('49.99'),
            description='A great mouse for gaming.',
        )

        response = self.client.get(reverse('shop'), {'q': 'wireless'})
        self.assertContains(response, 'Wireless Headphones')
        self.assertNotContains(response, 'Gaming Mouse')

    def test_wishlist_toggle_for_logged_in_user(self):
        user = get_user_model().objects.create_user(username='wishuser', password='StrongPass123!')
        self.client.force_login(user)

        response = self.client.post(reverse('toggle_wishlist', args=[self.product.slug]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(WishlistItem.objects.filter(user=user, product=self.product).exists())

        self.client.post(reverse('toggle_wishlist', args=[self.product.slug]))
        self.assertFalse(WishlistItem.objects.filter(user=user, product=self.product).exists())
