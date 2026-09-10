import json
import logging
import uuid
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.mail import send_mail
from django.db import transaction
from django.template import Context, Template
from django.shortcuts import redirect, render
from django.urls import reverse

from .models import Category, EmailTemplate, Order, OrderItem, Product, WishlistItem

logger = logging.getLogger(__name__)


def _cart_from_session(request):
    return request.session.get('cart', {})


def _save_cart(request, cart):
    request.session['cart'] = cart
    request.session.modified = True


def _cart_products(cart):
    return [(Product.objects.get(pk=product_id), int(quantity)) for product_id, quantity in cart.items()]


def _stock_error(cart):
    for product, quantity in _cart_products(cart):
        if quantity > product.stock_quantity:
            return f'{product.name} has only {product.stock_quantity} left in stock.'
    return None


def _send_order_confirmation(order):
    template = EmailTemplate.objects.filter(key='order_confirmation', enabled=True).first()
    if not template or order.confirmation_sent:
        return
    item_lines = '\n'.join(f'- {item.product.name} x {item.quantity}: N{item.subtotal():,.2f}' for item in order.items.select_related('product'))
    context = Context({'customer_name': order.customer_name, 'order_id': order.id, 'total': f'{order.total():,.2f}', 'items': item_lines})
    try:
        send_mail(Template(template.subject).render(context), Template(template.body).render(context), settings.DEFAULT_FROM_EMAIL, [order.email], fail_silently=False)
    except Exception:
        logger.exception('Could not send confirmation email for order %s', order.pk)
        return
    order.confirmation_sent = True
    order.save(update_fields=['confirmation_sent'])


def _complete_order(order):
    with transaction.atomic():
        locked_order = Order.objects.select_for_update().get(pk=order.pk)
        if not locked_order.inventory_reduced:
            for item in locked_order.items.all():
                product = Product.objects.select_for_update().get(pk=item.product_id)
                if item.quantity > product.stock_quantity:
                    raise ValueError(f'{product.name} has only {product.stock_quantity} left in stock.')
                product.stock_quantity -= item.quantity
                product.save(update_fields=['stock_quantity'])
            locked_order.inventory_reduced = True
        if locked_order.payment_method == 'paystack':
            locked_order.payment_status = 'paid'
        locked_order.save(update_fields=['inventory_reduced', 'payment_status'])
    _send_order_confirmation(locked_order)
    return locked_order


def _paystack_request(path, payload=None):
    secret_key = getattr(settings, 'PAYSTACK_SECRET_KEY', '')
    if not secret_key:
        raise RuntimeError('Paystack is not configured. Add PAYSTACK_SECRET_KEY to the environment.')
    data = json.dumps(payload).encode() if payload is not None else None
    request = Request(f'https://api.paystack.co/{path}', data=data, headers={'Authorization': f'Bearer {secret_key}', 'Content-Type': 'application/json'}, method='POST' if data else 'GET')
    try:
        with urlopen(request, timeout=15) as response:
            result = json.loads(response.read().decode())
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError('Paystack could not be reached. Please try again.') from exc
    if not result.get('status'):
        raise RuntimeError(result.get('message', 'Paystack rejected the request.'))
    return result


def home(request):
    products = Product.objects.all().order_by('-is_featured', '-created_at')
    categories = Category.objects.all()
    featured_product = products.filter(is_featured=True).first() or products.first()
    return render(request, 'index.html', {'products': products, 'categories': categories, 'active_page': 'home', 'featured_product': featured_product})


def shop(request):
    query = request.GET.get('q', '').strip()
    products = Product.objects.all().order_by('-is_featured', '-created_at')
    if query:
        products = products.filter(name__icontains=query) | products.filter(description__icontains=query)
    categories = Category.objects.all()
    return render(request, 'shop.html', {'products': products, 'categories': categories, 'active_page': 'shop', 'query': query})


def category_products(request, slug):
    category = Category.objects.get(slug=slug)
    products = Product.objects.filter(category=category).order_by('-is_featured', '-created_at')
    categories = Category.objects.all()
    return render(request, 'shop.html', {'products': products, 'categories': categories, 'active_page': 'shop', 'selected_category': category})


def product_detail(request, slug):
    product = Product.objects.get(slug=slug)
    is_wishlisted = False
    if request.user.is_authenticated:
        is_wishlisted = WishlistItem.objects.filter(user=request.user, product=product).exists()
    return render(request, 'single.html', {'product': product, 'active_page': 'shop', 'is_wishlisted': is_wishlisted})


def cart(request):
    cart = _cart_from_session(request)
    items = []
    total = Decimal('0.00')

    for product_id, quantity in cart.items():
        product = Product.objects.get(pk=product_id)
        subtotal = product.price * int(quantity)
        total += subtotal
        items.append({'product': product, 'quantity': int(quantity), 'subtotal': subtotal})

    if request.method == 'POST':
        form_cart = {}
        for key, value in request.POST.items():
            if key == 'csrfmiddlewaretoken':
                continue
            if value.isdigit() and int(value) > 0:
                form_cart[key] = int(value)
        stock_error = _stock_error(form_cart)
        if stock_error:
            messages.error(request, stock_error)
            return redirect('cart')
        _save_cart(request, form_cart)
        messages.success(request, 'Your cart has been updated.')
        return redirect('cart')

    return render(request, 'cart.html', {'items': items, 'total': total, 'active_page': 'cart'})


def add_to_cart(request, slug):
    product = Product.objects.get(slug=slug)
    cart = _cart_from_session(request)
    try:
        quantity = max(int(request.POST.get('quantity', 1)), 1)
    except (TypeError, ValueError):
        quantity = 1
    if cart.get(str(product.id), 0) + quantity > product.stock_quantity:
        messages.error(request, f'{product.name} has only {product.stock_quantity} left in stock.')
        return redirect('cart')
    cart[str(product.id)] = cart.get(str(product.id), 0) + quantity
    _save_cart(request, cart)
    messages.success(request, 'Added to cart successfully.')
    return redirect('cart')


def checkout(request):
    cart = _cart_from_session(request)
    stock_error = _stock_error(cart) if cart else None
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', 'cash')
        if not cart:
            messages.error(request, 'Your cart is empty.')
            return redirect('cart')
        if stock_error:
            messages.error(request, stock_error)
            return redirect('cart')
        reference = f'ELECTRO-{uuid.uuid4().hex[:20].upper()}' if payment_method == 'paystack' else None
        try:
            with transaction.atomic():
                order = Order.objects.create(
                    customer_name=request.POST.get('customer_name', ''),
                    email=request.POST.get('email', ''),
                    address=request.POST.get('address', ''),
                    payment_method=payment_method,
                    payment_status='pending',
                    payment_reference=reference,
                )
                for product, quantity in _cart_products(cart):
                    OrderItem.objects.create(order=order, product=product, quantity=quantity, price=product.price)
        except Exception:
            messages.error(request, 'We could not create your order. Please try again.')
            return redirect('checkout')

        if payment_method == 'paystack':
            try:
                result = _paystack_request('transaction/initialize', {
                    'amount': int(order.total() * 100),
                    'email': order.email,
                    'reference': order.payment_reference,
                    'callback_url': request.build_absolute_uri(reverse('paystack_callback')),
                    'metadata': {'order_id': order.id},
                })
            except RuntimeError as exc:
                order.delete()
                messages.error(request, str(exc))
                return redirect('checkout')
            request.session['pending_order_id'] = order.id
            return redirect(result['data']['authorization_url'])

        try:
            _complete_order(order)
        except ValueError as exc:
            order.delete()
            messages.error(request, str(exc))
            return redirect('cart')
        request.session['cart'] = {}
        request.session.modified = True
        messages.success(request, 'Order placed successfully. A confirmation email is on its way.')
        return redirect('home')

    items = []
    total = Decimal('0.00')
    for product, quantity in _cart_products(cart):
        subtotal = product.price * quantity
        total += subtotal
        items.append({'product': product, 'quantity': quantity, 'subtotal': subtotal})

    return render(request, 'checkout.html', {'items': items, 'total': total, 'active_page': 'checkout', 'stock_error': stock_error})


def paystack_callback(request):
    reference = request.GET.get('reference') or request.GET.get('trxref')
    if not reference:
        messages.error(request, 'We could not identify your payment.')
        return redirect('checkout')
    order = Order.objects.filter(payment_reference=reference).first()
    if not order:
        messages.error(request, 'This payment is not linked to an order.')
        return redirect('home')
    try:
        result = _paystack_request(f'transaction/verify/{quote(reference)}')
    except RuntimeError as exc:
        messages.error(request, str(exc))
        return redirect('checkout')
    if result.get('data', {}).get('status') != 'success':
        order.payment_status = 'failed'
        order.save(update_fields=['payment_status'])
        messages.error(request, 'Payment was not completed.')
        return redirect('checkout')
    try:
        _complete_order(order)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect('home')
    request.session['cart'] = {}
    request.session.pop('pending_order_id', None)
    request.session.modified = True
    messages.success(request, 'Payment confirmed. Your order and email receipt are ready.')
    return redirect('home')


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully.')
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form, 'active_page': 'account'})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            messages.success(request, 'You are now logged in.')
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form, 'active_page': 'account'})


def logout_view(request):
    logout(request)
    messages.success(request, 'You are now logged out.')
    return redirect('home')


def toggle_wishlist(request, slug):
    if not request.user.is_authenticated:
        messages.info(request, 'Please log in to manage your wishlist.')
        return redirect('login')

    product = Product.objects.get(slug=slug)
    wishlist_item = WishlistItem.objects.filter(user=request.user, product=product).first()
    if wishlist_item:
        wishlist_item.delete()
        messages.success(request, 'Removed from wishlist.')
    else:
        WishlistItem.objects.create(user=request.user, product=product)
        messages.success(request, 'Added to wishlist.')
    return redirect(request.META.get('HTTP_REFERER', 'home'))


def wishlist(request):
    if not request.user.is_authenticated:
        messages.info(request, 'Please log in to view your wishlist.')
        return redirect('login')

    items = WishlistItem.objects.filter(user=request.user).select_related('product')
    return render(request, 'wishlist.html', {'items': items, 'active_page': 'wishlist'})
