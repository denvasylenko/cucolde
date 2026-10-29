import pytest
from pydantic import ValidationError

from adaptive_form_agent.handoffs import DomainReport


def test_domain_report_carries_conclusions_and_requested_form_facts():
    report = DomainReport(
        status="partial",
        summary="The legal relationship is understood.",
        concepts=["ultimate parent company"],
        prerequisites=["A subsidiary relationship exists."],
        unknowns=["Whether the company is a subsidiary."],
        requestedFormFacts=["Current hasSubsidiary state"],
    )

    payload = report.model_dump(by_alias=True)
    assert payload["concepts"] == ["ultimate parent company"]
    assert payload["requestedFormFacts"] == ["Current hasSubsidiary state"]


def test_domain_report_rejects_unstructured_extra_fields():
    with pytest.raises(ValidationError):
        DomainReport(
            status="completed",
            summary="Done",
            arbitraryArtifact={"raw": "evidence"},
        )


def test_domain_report_rejects_unknown_status():
    with pytest.raises(ValidationError):
        DomainReport(status="waiting", summary="Not started")
