from __future__ import annotations

import json
import socket
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class LMStudioAPIError(RuntimeError):
    """Raised when LM Studio returns an invalid response or network error."""


class LMStudioClient:
    @staticmethod
    def _build_url(base_url: str, path: str) -> str:
        return f"{base_url.rstrip('/')}{path}"

    @staticmethod
    def _extract_http_error_message(exc: HTTPError) -> str:
        details = ""
        try:
            body = exc.read().decode("utf-8", errors="ignore")
            if body:
                parsed = json.loads(body)
                if isinstance(parsed, dict):
                    error_payload = parsed.get("error")
                    if isinstance(error_payload, dict):
                        details = str(error_payload.get("message", "")).strip()
                    elif isinstance(error_payload, str):
                        details = error_payload.strip()
                if not details:
                    details = body.strip()
        except Exception:
            details = ""

        if details:
            return f"HTTP {exc.code}: {details}"
        return f"HTTP {exc.code}: {exc.reason}"

    def _request_json(
        self,
        *,
        url: str,
        method: str,
        timeout_seconds: float,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data = None
        headers: dict[str, str] = {}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = Request(url=url, data=data, headers=headers, method=method)

        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            raise LMStudioAPIError(self._extract_http_error_message(exc)) from exc
        except URLError as exc:
            reason = exc.reason
            if isinstance(reason, socket.timeout):
                raise LMStudioAPIError("Tiempo de espera agotado al conectar con LM Studio.") from exc
            raise LMStudioAPIError(f"No se pudo conectar con LM Studio: {reason}") from exc
        except TimeoutError as exc:
            raise LMStudioAPIError("Tiempo de espera agotado al conectar con LM Studio.") from exc

        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise LMStudioAPIError("LM Studio devolvio una respuesta JSON invalida.") from exc

        if not isinstance(parsed, dict):
            raise LMStudioAPIError("LM Studio devolvio un formato de respuesta no esperado.")

        return parsed

    def list_models(self, base_url: str, timeout_seconds: float = 30.0) -> list[str]:
        url = self._build_url(base_url, "/models")
        payload = self._request_json(url=url, method="GET", timeout_seconds=timeout_seconds)

        models = payload.get("data")
        if not isinstance(models, list):
            raise LMStudioAPIError("No se pudo leer la lista de modelos de LM Studio.")

        model_ids: list[str] = []
        for item in models:
            if isinstance(item, dict):
                model_id = item.get("id")
                if isinstance(model_id, str) and model_id.strip():
                    model_ids.append(model_id.strip())

        return model_ids

    def chat_completion(
        self,
        *,
        base_url: str,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        timeout_seconds: float,
    ) -> str:
        url = self._build_url(base_url, "/chat/completions")
        request_payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        payload = self._request_json(
            url=url,
            method="POST",
            payload=request_payload,
            timeout_seconds=timeout_seconds,
        )

        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LMStudioAPIError("LM Studio no devolvio respuestas en 'choices'.")

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise LMStudioAPIError("El formato de respuesta de LM Studio no es valido.")

        message = first_choice.get("message")
        if not isinstance(message, dict):
            raise LMStudioAPIError("No se encontro el mensaje del asistente en la respuesta.")

        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise LMStudioAPIError("El contenido de la respuesta del modelo esta vacio.")

        return content.strip()
