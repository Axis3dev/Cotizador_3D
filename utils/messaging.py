"""Helpers to deliver quotations via email or WhatsApp."""

from __future__ import annotations

import mimetypes
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Dict

from models.cotizacion import Cotizacion


class MessagingError(RuntimeError):
    """Raised when sending a message fails."""


def send_email_with_pdf(config: Dict[str, object], quote: Cotizacion, pdf_path: Path) -> None:
    if not quote.cliente.correo:
        raise MessagingError("La cotización no tiene correo de cliente definido.")
    host = config.get("host")
    if not host:
        raise MessagingError("Configura el servidor SMTP en la sección de integraciones.")
    port = int(config.get("puerto", 587))
    usuario = config.get("usuario") or config.get("remitente")
    password = config.get("password")
    remitente = config.get("remitente") or usuario
    usar_tls = bool(config.get("usar_tls", True))

    if not usuario or not password:
        raise MessagingError("Faltan credenciales SMTP (usuario o password).")

    message = EmailMessage()
    message["Subject"] = f"Cotización {quote.folio}"
    message["From"] = remitente
    message["To"] = quote.cliente.correo
    body = config.get("mensaje", "Adjuntamos la cotización solicitada.")
    message.set_content(str(body))

    mime_type, _ = mimetypes.guess_type(pdf_path)
    maintype, subtype = (mime_type or "application/pdf").split("/", 1)
    with pdf_path.open("rb") as fh:
        message.add_attachment(
            fh.read(),
            maintype=maintype,
            subtype=subtype,
            filename=pdf_path.name,
        )

    try:
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            if usar_tls:
                smtp.starttls()
            smtp.login(usuario, password)
            smtp.send_message(message)
    except Exception as exc:  # pragma: no cover - network I/O
        raise MessagingError(str(exc)) from exc


def send_whatsapp_placeholder(config: Dict[str, object], quote: Cotizacion, pdf_path: Path) -> None:
    numero_negocio = config.get("numero")
    if not quote.cliente.celular:
        raise MessagingError("No hay número de celular del cliente.")
    if not numero_negocio:
        raise MessagingError("Configura el número de WhatsApp del negocio.")
    # Placeholder: in a real integration you'd call the provider's API here.
    mensaje_base = config.get(
        "mensaje_base",
        "Hola {cliente}, adjuntamos tu cotización {folio}.",
    )
    mensaje = mensaje_base.format(cliente=quote.cliente.nombre, folio=quote.folio)
    log_path = pdf_path.with_suffix(".whatsapp.txt")
    with log_path.open("w", encoding="utf-8") as fh:
        fh.write(
            f"Enviar a: {quote.cliente.celular}\n"
            f"Desde: {numero_negocio}\n"
            f"Mensaje: {mensaje}\n"
            f"Adjunto: {pdf_path.name}\n"
        )


__all__ = ["MessagingError", "send_email_with_pdf", "send_whatsapp_placeholder"]
