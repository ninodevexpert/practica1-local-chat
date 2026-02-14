from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from src.chat_service import ChatService
from src.config import AppConfig
from src.lmstudio_client import LMStudioAPIError, LMStudioClient


class ChatUI:
    def __init__(self, *, config: AppConfig, client: LMStudioClient, chat_service: ChatService) -> None:
        self.config = config
        self.client = client
        self.chat_service = chat_service
        self.root = tk.Tk()
        self.root.title("Local Chat - LM Studio")
        self.root.geometry("900x650")
        self.root.minsize(760, 560)

        self.base_url_var = tk.StringVar(value=self.config.base_url)
        self.model_var = tk.StringVar()
        self.temperature_var = tk.StringVar(value=str(self.config.default_temperature))
        self.max_tokens_var = tk.StringVar(value=str(self.config.default_max_tokens))
        self.status_var = tk.StringVar(value="Listo.")
        self._request_in_progress = False

        self._build_layout()
        self._bind_events()
        self.root.after(100, self.refresh_models)

    def run(self) -> None:
        self.root.mainloop()

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)

        endpoint_frame = ttk.Frame(self.root, padding=(12, 12, 12, 6))
        endpoint_frame.grid(row=0, column=0, sticky="ew")
        endpoint_frame.columnconfigure(1, weight=1)

        ttk.Label(endpoint_frame, text="LM Studio base URL").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.base_url_entry = ttk.Entry(endpoint_frame, textvariable=self.base_url_var)
        self.base_url_entry.grid(row=0, column=1, sticky="ew")
        self.refresh_button = ttk.Button(endpoint_frame, text="Refrescar modelos", command=self.refresh_models)
        self.refresh_button.grid(row=0, column=2, padx=(8, 0))

        controls_frame = ttk.Frame(self.root, padding=(12, 0, 12, 6))
        controls_frame.grid(row=1, column=0, sticky="ew")
        for col in range(7):
            controls_frame.columnconfigure(col, weight=0)
        controls_frame.columnconfigure(1, weight=1)

        ttk.Label(controls_frame, text="Modelo").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.model_combobox = ttk.Combobox(
            controls_frame,
            textvariable=self.model_var,
            state="readonly",
            values=[],
        )
        self.model_combobox.grid(row=0, column=1, sticky="ew", padx=(0, 12))

        ttk.Label(controls_frame, text="Temperature").grid(row=0, column=2, sticky="w", padx=(0, 8))
        self.temperature_entry = ttk.Entry(controls_frame, width=8, textvariable=self.temperature_var)
        self.temperature_entry.grid(row=0, column=3, sticky="w", padx=(0, 12))

        ttk.Label(controls_frame, text="Max tokens").grid(row=0, column=4, sticky="w", padx=(0, 8))
        self.max_tokens_entry = ttk.Entry(controls_frame, width=10, textvariable=self.max_tokens_var)
        self.max_tokens_entry.grid(row=0, column=5, sticky="w", padx=(0, 12))

        self.clear_button = ttk.Button(controls_frame, text="Limpiar chat", command=self.clear_chat)
        self.clear_button.grid(row=0, column=6, sticky="e")

        chat_frame = ttk.Frame(self.root, padding=(12, 0, 12, 8))
        chat_frame.grid(row=2, column=0, sticky="nsew")
        chat_frame.columnconfigure(0, weight=1)
        chat_frame.rowconfigure(0, weight=1)

        self.chat_text = tk.Text(chat_frame, wrap="word", state="disabled")
        self.chat_text.grid(row=0, column=0, sticky="nsew")
        chat_scrollbar = ttk.Scrollbar(chat_frame, orient="vertical", command=self.chat_text.yview)
        chat_scrollbar.grid(row=0, column=1, sticky="ns")
        self.chat_text.configure(yscrollcommand=chat_scrollbar.set)

        input_frame = ttk.Frame(self.root, padding=(12, 0, 12, 8))
        input_frame.grid(row=3, column=0, sticky="ew")
        input_frame.columnconfigure(0, weight=1)

        self.message_input = tk.Text(input_frame, height=4, wrap="word")
        self.message_input.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.send_button = ttk.Button(input_frame, text="Enviar", command=self.send_message)
        self.send_button.grid(row=0, column=1, sticky="ns")
        self.send_button.state(["disabled"])

        status_bar = ttk.Label(self.root, textvariable=self.status_var, anchor="w", padding=(12, 0, 12, 12))
        status_bar.grid(row=4, column=0, sticky="ew")

    def _bind_events(self) -> None:
        self.message_input.bind("<Return>", self._on_enter_pressed)
        self.model_combobox.bind("<<ComboboxSelected>>", lambda _: self._update_send_state())

    def _on_enter_pressed(self, event: tk.Event) -> str | None:
        if event.state & 0x0001:
            return None
        self.send_message()
        return "break"

    def _set_status(self, message: str) -> None:
        self.status_var.set(message)

    def _update_send_state(self) -> None:
        selected_model = self.model_var.get().strip()
        if self._request_in_progress or not selected_model:
            self.send_button.state(["disabled"])
        else:
            self.send_button.state(["!disabled"])

    def _append_chat(self, role: str, content: str) -> None:
        self.chat_text.configure(state="normal")
        self.chat_text.insert("end", f"{role}: {content}\n\n")
        self.chat_text.see("end")
        self.chat_text.configure(state="disabled")

    def clear_chat(self) -> None:
        self.chat_service.reset_history()
        self.chat_text.configure(state="normal")
        self.chat_text.delete("1.0", "end")
        self.chat_text.configure(state="disabled")
        self._set_status("Historial limpiado.")

    def refresh_models(self) -> None:
        base_url = self.base_url_var.get().strip()
        if not base_url:
            messagebox.showerror("URL invalida", "Debes indicar una URL base valida.")
            return

        self._set_status("Conectando...")
        self.refresh_button.state(["disabled"])

        def worker() -> None:
            try:
                models = self.client.list_models(base_url=base_url, timeout_seconds=self.config.timeout_seconds)
                self.root.after(0, lambda models=models: self._on_models_loaded(models))
            except Exception as exc:  # noqa: BLE001
                self.root.after(0, lambda exc=exc: self._on_models_error(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _on_models_loaded(self, models: list[str]) -> None:
        self.refresh_button.state(["!disabled"])
        self.model_combobox["values"] = models
        if models:
            current = self.model_var.get().strip()
            if current not in models:
                self.model_var.set(models[0])
            self._set_status(f"Modelos cargados: {len(models)}")
        else:
            self.model_var.set("")
            self._set_status("No se encontraron modelos en LM Studio.")
        self._update_send_state()

    def _on_models_error(self, exc: Exception) -> None:
        self.refresh_button.state(["!disabled"])
        self.model_var.set("")
        self.model_combobox["values"] = []
        self._update_send_state()
        self._set_status(f"Error: {exc}")
        if isinstance(exc, LMStudioAPIError):
            messagebox.showerror("Error de LM Studio", str(exc))
        else:
            messagebox.showerror("Error", "Fallo inesperado al cargar modelos.")

    def _read_generation_params(self) -> tuple[float, int] | None:
        try:
            temperature = float(self.temperature_var.get().strip())
            max_tokens = int(self.max_tokens_var.get().strip())
        except ValueError:
            messagebox.showerror("Parametros invalidos", "Temperature debe ser decimal y max_tokens entero.")
            return None

        if max_tokens <= 0:
            messagebox.showerror("Parametros invalidos", "max_tokens debe ser mayor que cero.")
            return None

        return temperature, max_tokens

    def send_message(self) -> None:
        if self._request_in_progress:
            return

        model = self.model_var.get().strip()
        if not model:
            messagebox.showerror("Modelo requerido", "Selecciona un modelo antes de enviar.")
            return

        message = self.message_input.get("1.0", "end-1c").strip()
        if not message:
            self._set_status("Escribe un mensaje para enviar.")
            return

        params = self._read_generation_params()
        if params is None:
            return
        temperature, max_tokens = params

        self.chat_service.add_user_message(message)
        self._append_chat("Tú", message)
        self.message_input.delete("1.0", "end")

        self._request_in_progress = True
        self._update_send_state()
        self._set_status("Enviando...")

        base_url = self.base_url_var.get().strip()
        messages = self.chat_service.build_messages()

        def worker() -> None:
            try:
                answer = self.client.chat_completion(
                    base_url=base_url,
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout_seconds=self.config.timeout_seconds,
                )
                self.root.after(0, lambda answer=answer: self._on_message_sent_success(answer))
            except Exception as exc:  # noqa: BLE001
                self.root.after(0, lambda exc=exc: self._on_message_sent_error(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _on_message_sent_success(self, answer: str) -> None:
        self.chat_service.add_assistant_message(answer)
        self._append_chat("Asistente", answer)
        self._request_in_progress = False
        self._update_send_state()
        self._set_status("Listo.")

    def _on_message_sent_error(self, exc: Exception) -> None:
        self._append_chat("Sistema", f"Error al consultar LM Studio: {exc}")
        self._request_in_progress = False
        self._update_send_state()
        self._set_status(f"Error: {exc}")
