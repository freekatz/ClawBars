import ssl as _ssl
from urllib.parse import urlparse, parse_qs

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

_CLOUD_HOSTS = (".rds.aliyuncs.com", ".rds.amazonaws.com", "supabase.com", ".neon.tech")


def _get_ssl_context(host: str, ssl_mode: str | None) -> _ssl.SSLContext | bool | None:
    """Create SSL context based on config and host (same logic as sql2.py)."""
    if ssl_mode in ("disable", "false"):
        return False

    if ssl_mode in ("require", "true") or any(h in host for h in _CLOUD_HOSTS):
        ctx = _ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = _ssl.CERT_NONE
        return ctx

    return None


def _engine_kwargs() -> dict:
    """Build extra kwargs for create_async_engine based on DATABASE_URL."""
    kwargs: dict = {"echo": settings.debug, "future": True}
    url = settings.database_url

    parsed = urlparse(url)
    host = parsed.hostname or ""
    qs = parse_qs(parsed.query)
    ssl_mode = qs.get("sslmode", [None])[0]

    ssl_ctx = _get_ssl_context(host, ssl_mode)

    connect_args: dict = {}
    if ssl_ctx is not None:
        connect_args["ssl"] = ssl_ctx
    kwargs["connect_args"] = connect_args

    # Strip sslmode from URL since it's handled via connect_args
    if ssl_mode is not None:
        clean_url = url.split("?")[0]
        remaining = {k: v[0] for k, v in qs.items() if k != "sslmode"}
        if remaining:
            clean_url += "?" + "&".join(f"{k}={v}" for k, v in remaining.items())
        kwargs["url"] = clean_url
    else:
        kwargs["url"] = url

    return kwargs


_kw = _engine_kwargs()
_url = _kw.pop("url")
engine = create_async_engine(_url, **_kw)
session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
