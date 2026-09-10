"""
Entry point cPanel's Phusion Passenger looks for when you create the app
via "Setup Python App". Point the app's "Application startup file" at this
file and its "Application Entry point" at `application` (the default).

This just delegates to the real Django WSGI app so we don't duplicate any
settings/bootstrap logic.
"""

import os
import sys

# cPanel's Python App feature puts the project directory on sys.path
# automatically, but we add it explicitly too in case this is wired up by
# hand (e.g. a custom Passenger vhost outside the cPanel UI).
sys.path.insert(0, os.path.dirname(__file__))

from electro_bootstrap.wsgi import application  # noqa: E402
