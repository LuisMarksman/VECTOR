"""FastAPI dependencies for accessing shared services."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from app.services import Services


def get_services(request: Request) -> Services:
    """Return the process-wide :class:`Services` held on ``app.state``."""
    return request.app.state.services


#: Reusable typed dependency, e.g. ``def route(services: ServicesDep): ...``
ServicesDep = Annotated[Services, Depends(get_services)]
