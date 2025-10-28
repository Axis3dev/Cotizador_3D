"""Entry point for the Axis 3D quotation system using Flet."""

from __future__ import annotations

import flet as ft

from storage.clients_store import ClientsStore
from storage.config_store import ConfigStore
from storage.orders_store import OrdersStore
from storage.quotes_store import QuoteStore
from ui.flet_app import Axis3DFletApp


def main(page: ft.Page) -> None:
    """Launch the Flet interface."""

    config_store = ConfigStore()
    clients_store = ClientsStore()
    quote_store = QuoteStore()
    orders_store = OrdersStore()

    app = Axis3DFletApp(
        page=page,
        config_store=config_store,
        clients_store=clients_store,
        quote_store=quote_store,
        orders_store=orders_store,
    )
    app.mount()


if __name__ == "__main__":  # pragma: no cover - manual execution entry
    ft.app(target=main)
