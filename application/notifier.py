from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_DIR / ".env")


def _parse_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "oui"}


def is_smtp_enabled() -> bool:
    return _parse_bool(os.getenv("SMTP_ENABLED"), default=False)


def send_email(subject: str, body: str) -> bool:
    """
    Envoie un e-mail via SMTP si SMTP_ENABLED est actif.
    Ne lève jamais d'exception afin de ne pas interrompre le scraping.
    """
    if not is_smtp_enabled():
        return False

    host = (os.getenv("SMTP_HOST") or "smtp.gmail.com").strip()
    port_raw = (os.getenv("SMTP_PORT") or "587").strip()
    user = (os.getenv("SMTP_USER") or "").strip()
    password = (os.getenv("SMTP_PASSWORD") or "").replace(" ", "").strip()
    sender = (os.getenv("SMTP_FROM") or user).strip()
    recipient = (os.getenv("ADMIN_EMAIL") or user).strip()
    use_ssl = _parse_bool(os.getenv("SMTP_USE_SSL"), default=False)
    use_tls = _parse_bool(os.getenv("SMTP_USE_TLS"), default=not use_ssl)

    if not host or not user or not password or not recipient:
        print("[notifier] Configuration SMTP incomplète : vérifiez SMTP_HOST, SMTP_USER, SMTP_PASSWORD, ADMIN_EMAIL.")
        return False

    try:
        port = int(port_raw)
    except ValueError:
        port = 465 if use_ssl else 587

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender or user
    msg["To"] = recipient
    msg.set_content(body)

    try:
        context = ssl.create_default_context()
        if use_ssl or port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=20, context=context) as server:
                server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=20) as server:
                server.ehlo()
                if use_tls:
                    server.starttls(context=context)
                    server.ehlo()
                server.login(user, password)
                server.send_message(msg)
        return True
    except Exception as exc:
        print(f"[notifier] Échec d'envoi SMTP ({subject}) : {exc}")
        return False

def send_email_async(subject: str, body: str) -> None:
    """Lance send_email dans un thread daemon sans bloquer l'appelant."""
    import threading

    def _runner() -> None:
        try:
            send_email(subject, body)
        except Exception as exc:
            print(f"[notifier] Erreur thread async ({subject}) : {exc}")

    threading.Thread(target=_runner, daemon=True).start()
