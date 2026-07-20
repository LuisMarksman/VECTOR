"""Core domain logic for the VECTOR server.

The core layer is deliberately independent of FastAPI so it can be reused from
tests, background workers or a CLI. The HTTP layer in :mod:`app.api` is a thin
adapter over these services.
"""
