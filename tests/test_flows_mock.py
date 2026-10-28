from __future__ import annotations

from medbh_rpa.flows import get_flow
from medbh_rpa.ui.mock import MockUi
from medbh_rpa.config import Settings


def test_buscar_e_agendar_mock() -> None:
    ui = MockUi(Settings())
    found = get_flow("buscar_paciente")(ui, {"nome": "Ana"})
    assert found["found"] is True

    appt = get_flow("agendar")(
        ui,
        {
            "patient_id": found["patient_id"],
            "parceiro": "Clínica Carijós",
            "procedimento": "Consulta",
            "data": "2026-10-28",
            "horario": "16:00",
        },
    )
    assert appt["atendimento_id"].startswith("MOCK-")
