from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class UiAdapter(ABC):
    """Contrato mínimo da UI do msAdmin. Implementações reais vêm após a Fase 0."""

    @abstractmethod
    def healthcheck(self) -> dict[str, Any]:
        """Retorna status do ambiente / janela do sistema."""

    @abstractmethod
    def ensure_logged_in(self) -> None:
        """Garante sessão aberta no msAdmin."""

    @abstractmethod
    def find_patient(self, *, cpf: str | None = None, nome: str | None = None) -> dict[str, Any]:
        """Busca paciente. Retorno padronizado: found, patient_id, nome."""

    @abstractmethod
    def create_appointment(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Cria agendamento. Retorno: atendimento_id, status."""

    @abstractmethod
    def register_payment(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Registra cobrança / gera link."""

    @abstractmethod
    def emit_guia(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Emite guia impressa e/ou digital."""

    @abstractmethod
    def screenshot(self, path: Path) -> Path:
        """Salva captura para diagnóstico de falha."""
