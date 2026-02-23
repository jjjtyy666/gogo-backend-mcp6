import logging
import inspect
import functools
import time
from typing import Optional, Iterable, Any


DEFAULT_REDACT_KEYS = {"password", "token", "secret", "api_key", "authorization", "db_url", "database_url"}


def _redact(obj: Any, redact_keys: Optional[Iterable[str]] = None) -> Any:
    """Return a redacted-friendly representation of obj. For mappings, redact keys; for other objects, return truncated repr."""
    redact_keys = set(k.lower() for k in (redact_keys or [])) | DEFAULT_REDACT_KEYS
    try:
        if isinstance(obj, dict):
            out = {}
            for k, v in obj.items():
                if str(k).lower() in redact_keys:
                    out[k] = "<REDACTED>"
                else:
                    out[k] = _redact(v, redact_keys)
            return out
        # for lists/tuples, map recursively but keep type
        if isinstance(obj, (list, tuple)):
            mapped = [_redact(v, redact_keys) for v in obj]
            return type(obj)(mapped)
        # for simple values, return repr truncated
        r = repr(obj)
        if len(r) > 200:
            return r[:200] + "...<truncated>"
        return obj
    except Exception:
        # Fallback to safe repr
        try:
            return repr(obj)[:200]
        except Exception:
            return "<UNREPRESENTABLE>"


def log_calls(redact_keys: Optional[Iterable[str]] = None, level: int = logging.INFO):
    """Decorator factory that logs entry, exit (with duration) and exceptions for sync and async functions.

    Usage:
        @log_calls()
        def f(...):
            ...
    """

    def decorator(func):
        logger = logging.getLogger(func.__module__)
        is_coro = inspect.iscoroutinefunction(func)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                start = time.time()
                try:
                    bound = inspect.signature(func).bind_partial(*args, **kwargs)
                    bound.apply_defaults()
                    args_dict = {k: _redact(v, redact_keys) for k, v in bound.arguments.items()}
                except Exception:
                    args_dict = "<cannot-inspect-args>"
                logger.log(level, "ENTER %s.%s args=%s", func.__module__, func.__qualname__, args_dict)
                result = await func(*args, **kwargs)
                duration = time.time() - start
                logger.log(level, "EXIT  %s.%s duration=%.6fs result=%s", func.__module__, func.__qualname__, duration, _redact(result, redact_keys))
                return result
            except Exception:
                logger.exception("EXCEPT %s.%s", func.__module__, func.__qualname__)
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                start = time.time()
                try:
                    bound = inspect.signature(func).bind_partial(*args, **kwargs)
                    bound.apply_defaults()
                    args_dict = {k: _redact(v, redact_keys) for k, v in bound.arguments.items()}
                except Exception:
                    args_dict = "<cannot-inspect-args>"
                logger.log(level, "ENTER %s.%s args=%s", func.__module__, func.__qualname__, args_dict)
                result = func(*args, **kwargs)
                duration = time.time() - start
                logger.log(level, "EXIT  %s.%s duration=%.6fs result=%s", func.__module__, func.__qualname__, duration, _redact(result, redact_keys))
                return result
            except Exception:
                logger.exception("EXCEPT %s.%s", func.__module__, func.__qualname__)
                raise

        return async_wrapper if is_coro else sync_wrapper

    return decorator
