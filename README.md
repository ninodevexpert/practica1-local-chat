# Módulo 5: Práctica 1 - Conectándonos a modelos en local

Aplicación de escritorio en Python con `tkinter` para chatear con modelos locales servidos por **LM Studio** usando su API compatible con OpenAI (`/v1/models` y `/v1/chat/completions`).

## Objetivo

Construir una interfaz básica de chat que permita:

- Cargar modelos disponibles desde LM Studio.
- Seleccionar un modelo desde la UI.
- Enviar mensajes y visualizar respuestas.
- Mantener historial de conversación en memoria durante la sesión.

## Requisitos

- Python 3.9+ (recomendado 3.13 en macOS).
- LM Studio ejecutándose en local con servidor API activo.

## Ejecución

Desde la raíz del proyecto:

```bash
.venv/bin/python main.py
```

Si usas `uv`:

```bash
uv run .venv/bin/python main.py
```

## Configuración de conexión

La UI trae por defecto:

- `base_url`: `http://127.0.0.1:1234/v1`
- `temperature`: `0.7`
- `max_tokens`: `512`

## Estructura del proyecto

- `main.py`: punto de entrada de la app.
- `src/config.py`: configuración global (`AppConfig`).
- `src/lmstudio_client.py`: cliente HTTP para LM Studio.
- `src/chat_service.py`: historial de conversación en memoria.
- `src/ui.py`: interfaz `tkinter` y orquestación de eventos.
- `tests/test_lmstudio_client.py`: pruebas unitarias del cliente API.

## Funcionalidades implementadas

- Refresco de modelos (`GET /v1/models`).
- Selector de modelo en `Combobox`.
- Chat no streaming (`POST /v1/chat/completions`).
- Manejo de errores de conexión y formato de respuesta.
- UI no bloqueante mediante `threading` + `Tk.after`.

