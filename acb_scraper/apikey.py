"""Descubrimiento de la cabecera pública X-APIKEY embebida en el bundle Next.js de acb.com."""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path

import httpx

log = logging.getLogger("acb.apikey")

HOME_URL = "https://www.acb.com/"
SITE_ORIGIN = "https://acb.com"
# Valor documentado el 2026-10-12 y confirmado el 2026-11-02. Solo se usa si el descubrimiento falla.
FALLBACK_KEY = "0dd94928-6f57-4c08-a3bd-b1b2f092976e"
KEY_RE = re.compile(r'apiKey\\?"?\s*:\s*\\?"?([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})')
CHUNK_RE = re.compile(r'(/_next/static/[^"\']+\.js)')
BROWSER_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def discover_key(timeout: float = 40.0) -> str | None:
    """Descarga la portada (siguiendo la redirección a /es/liga) y busca la clave en el HTML y en los chunks JS."""
    with httpx.Client(follow_redirects=True, timeout=timeout, headers={"User-Agent": BROWSER_UA}) as http:
        try:
            html = http.get(HOME_URL).text
        except httpx.HTTPError as exc:
            log.warning("no se pudo descargar la portada: %s", exc)
            return None
        m = KEY_RE.search(html)
        if m:
            return m.group(1)
        chunks = sorted(set(CHUNK_RE.findall(html)))
        log.info("clave no está en el HTML; revisando %d chunks", len(chunks))
        for chunk in chunks:
            try:
                js = http.get(SITE_ORIGIN + chunk).text
            except httpx.HTTPError:
                continue
            m = KEY_RE.search(js)
            if m:
                log.info("clave encontrada en %s", chunk)
                return m.group(1)
    return None


def load_key(cache_path: Path, max_age_days: float = 7.0, force: bool = False) -> str:
    """Devuelve la clave cacheada si es reciente; si no, la redescubre. Último recurso: FALLBACK_KEY."""
    if not force and cache_path.exists():
        try:
            data = json.loads(cache_path.read_text())
            if time.time() - data.get("fetched_at", 0) < max_age_days * 86400 and data.get("key"):
                return data["key"]
        except (json.JSONDecodeError, OSError):
            pass
    key = discover_key()
    if key is None:
        log.warning("usando la clave de respaldo documentada")
        key = FALLBACK_KEY
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps({"key": key, "fetched_at": time.time()}))
    return key
