from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from aipf.providers.base import ProviderError, ProviderErrorCode


def post_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: int) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - URL comes from trusted config
            value = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code in {401, 403}:
            code, retryable = ProviderErrorCode.AUTHENTICATION, False
        elif exc.code == 429:
            code, retryable = ProviderErrorCode.RATE_LIMIT, True
        else:
            code, retryable = ProviderErrorCode.NETWORK, exc.code >= 500
        raise ProviderError(code, f"provider HTTP error: {exc.code}", retryable=retryable) from exc
    except (TimeoutError, URLError) as exc:
        reason = getattr(exc, "reason", exc)
        is_timeout = isinstance(reason, TimeoutError)
        code = ProviderErrorCode.TIMEOUT if is_timeout else ProviderErrorCode.NETWORK
        raise ProviderError(code, "provider request failed", retryable=True) from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProviderError(ProviderErrorCode.INVALID_RESPONSE, "provider returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise ProviderError(ProviderErrorCode.INVALID_RESPONSE, "provider response must be an object")
    return value
