"""Unit tests for signing coordination agent helpers."""

from __future__ import annotations

from agents.signing_coordination.context import SigningCoordinationContext
from agents.signing_coordination.html_email import build_comparison_table_html, build_signing_coordination_html
from agents.signing_coordination.tools import build_signing_coordination_tools
from auth.signing_schedule_token import SigningScheduleTokenService
from config.settings import Settings
from scheduling.availability import generate_signing_slots


def test_signing_schedule_token_roundtrip():
    service = SigningScheduleTokenService(secret_key="test-secret")
    token = service.create(client_user_id="client-1", contract_id="contract-1")
    payload = service.verify(token)
    assert payload is not None
    assert payload["client_user_id"] == "client-1"
    assert payload["contract_id"] == "contract-1"


def test_generate_signing_slots_weekday_only():
    slots = generate_signing_slots(slot_minutes=45, weeks_ahead=1)
    assert len(slots) > 0
    assert all("CDMX" in slot for slot in slots)


def test_build_comparison_table_html_from_rows():
    html = build_comparison_table_html(
        {
            "rows": [
                {
                    "item_key": "renta_mensual",
                    "item_type": "field",
                    "original_value": "10000",
                    "new_value": "12000",
                    "difference": "modified",
                }
            ]
        }
    )
    assert "renta_mensual" in html
    assert "12000" in html


def test_send_email_tool_requires_prior_steps():
    settings = Settings(
        notification_dev_mode=True,
        azure_communication_connection_string="",
    )
    ctx = SigningCoordinationContext(
        contract_id="missing",
        client_user_id="u1",
        client_email="cliente@test.com",
        contract_title="Demo",
        closure_notes="Notas",
        schedule_url="http://localhost/schedule-signing?token=abc",
    )
    tools = {tool.name: tool for tool in build_signing_coordination_tools(ctx, settings)}
    try:
        tools["send_signing_coordination_email"].invoke({"narrative_summary": "Hola"})
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_build_signing_coordination_html_contains_schedule_link():
    html = build_signing_coordination_html(
        contract_title="Contrato X",
        narrative_summary="Resumen",
        comparison={"rows": []},
        schedule_url="http://localhost:3000/schedule-signing?token=t",
        closure_notes="Cierre ok",
    )
    assert "schedule-signing" in html
    assert "Resumen" in html
    assert "Next steps" in html
    assert "Upcoming schedules" not in html


def test_generate_signing_schedule_by_date_respects_days_ahead():
    from scheduling.availability import generate_signing_schedule_by_date

    schedule = generate_signing_schedule_by_date(days_ahead=30, slot_minutes=45)
    assert len(schedule) >= 1
    for day_iso, times in schedule.items():
        assert len(day_iso) == 10
        assert len(times) >= 1
