from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path("/home/randev/projets/Linkendin")
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from application.notifier import send_email


def _get_service_status(unit: str = "linkedin-scraper.service") -> str:
    try:
        res = subprocess.run(
            ["systemctl", "is-active", unit],
            capture_output=True,
            text=True,
            timeout=10,
        )
        out = (res.stdout or res.stderr or "").strip()
        return out or "unknown"
    except Exception as exc:
        return f"error ({exc})"


def _get_recent_logs(unit: str = "linkedin-scraper.service", lines: int = 25) -> str:
    try:
        res = subprocess.run(
            ["journalctl", "-u", unit, "-n", str(lines), "--no-pager"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        text = (res.stdout or res.stderr or "").strip()
        return text[-3500:] if text else "(Aucun log disponible)"
    except Exception as exc:
        return f"(Erreur lecture logs : {exc})"


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "daily"
    unit = "linkedin-scraper.service"
    status = _get_service_status(unit)
    logs = _get_recent_logs(unit, lines=25 if mode == "failure" else 20)

    if mode == "failure":
        subject = "[LinkedIn Scraper] Échec ou arrêt du service systemd"
        body = f"État actuel du service ({unit}) : {status}\n\nDerniers logs :\n{logs}"
    else:
        subject = f"[LinkedIn Scraper] Rapport quotidien 09h00 ({status})"
        body = f"État actuel du service ({unit}) : {status}\n\nDerniers logs :\n{logs}"

    ok = send_email(subject, body)
    print(f"NOTIFY mode={mode} status={status} sent={ok}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
