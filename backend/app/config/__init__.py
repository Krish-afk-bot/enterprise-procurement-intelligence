"""Configuration package.

Intentionally import-light: ``app.config.settings`` is imported by nearly every
module (including ``app.db.session``), so this package must not eagerly import
``app.config.container``, which itself depends on the database session factory.
Import from the concrete modules instead::

    from app.config.settings import get_settings
    from app.config.container import get_container
"""
