"""Shared helpers to embed the business logo into exports."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas

try:  # pragma: no cover - optional dependency for typing
    from openpyxl.drawing.image import Image as XLImage
    from openpyxl.worksheet.worksheet import Worksheet
except Exception:  # pragma: no cover - openpyxl might not be present during type checking
    XLImage = None  # type: ignore
    Worksheet = Any  # type: ignore


ALLOWED_LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def _to_path(value: str | os.PathLike[str] | None) -> Path | None:
    if not value:
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    return path


def resolve_logo_path(source: dict[str, Any] | str | Path | None) -> Path | None:
    """Return a validated logo path if the file exists and has an allowed extension."""

    if isinstance(source, (str, os.PathLike)):
        path = _to_path(source)
    elif isinstance(source, dict):
        logo_value = source.get("logo_path") or source.get("logo")
        path = _to_path(str(logo_value)) if logo_value else None
    else:
        path = None

    if not path or not path.exists() or not path.is_file():
        return None
    if path.suffix.lower() not in ALLOWED_LOGO_EXTENSIONS:
        return None
    return path


def draw_logo(canvas: Canvas, logo: dict[str, Any] | str | Path | None, *, x_mm: float = 15.0, y_mm: float = 265.0, w_mm: float = 30.0) -> bool:
    """Draw the configured logo on ``canvas`` returning ``True`` if it succeeded."""

    path = resolve_logo_path(logo)
    if not path:
        return False
    try:
        image = ImageReader(path)
        img_w, img_h = image.getSize()
        width = w_mm * mm
        height = (img_h / img_w) * width
        canvas.drawImage(
            image,
            x_mm * mm,
            y_mm * mm,
            width=width,
            height=height,
            preserveAspectRatio=True,
            mask="auto",
        )
        return True
    except Exception as exc:  # pragma: no cover - depends on reportlab internals
        logging.getLogger(__name__).warning("No se pudo dibujar el logo: %s", exc)
        return False


def add_logo_to_sheet(sheet: Worksheet, logo: dict[str, Any] | str | Path | None, cell: str = "A1") -> bool:
    """Insert the logo image into an Excel sheet returning ``True`` if it succeeded."""

    if XLImage is None:
        logging.getLogger(__name__).warning("openpyxl no está disponible para insertar el logo en Excel")
        return False

    path = resolve_logo_path(logo)
    if not path:
        return False
    try:
        image = XLImage(str(path))
        sheet.add_image(image, cell)
        return True
    except Exception as exc:  # pragma: no cover - depends on pillow/openpyxl
        logging.getLogger(__name__).warning("No se pudo insertar el logo en Excel: %s", exc)
        return False


__all__ = ["resolve_logo_path", "draw_logo", "add_logo_to_sheet"]
