"""Root aiogram router. Feature routers are included here as they are implemented."""

from aiogram import Router


def build_router() -> Router:
    """Return the root router that the dispatcher is built with.

    Output: an empty `Router`; no handlers are registered in the template.
    """
    return Router(name="root")
