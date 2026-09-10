from .views import _cart_from_session


def cart(request):
    """Expose the cart item count to every template (used for the header badge)."""
    session_cart = _cart_from_session(request)
    cart_count = sum(int(quantity) for quantity in session_cart.values())
    return {'cart_count': cart_count}
