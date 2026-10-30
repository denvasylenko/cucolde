import pytest
from pydantic import ValidationError

from adaptive_form_agent.handoffs import (
    DomainReport,
    FillerReport,
    FormIntelligenceReport,
)


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


def test_form_intelligence_report_carries_names_not_component_records():
    report = FormIntelligenceReport(
        status="completed",
        findings=["Two required fields are empty."],
        components=["subsidiaryName"],
        actions=[{"componentName": "saveSubsidiary", "event": "onPartialSubmit"}],
    )

    payload = report.model_dump(by_alias=True)
    assert payload["components"] == ["subsidiaryName"]
    assert payload["actions"] == [
        {"componentName": "saveSubsidiary", "event": "onPartialSubmit"}
    ]
    with pytest.raises(ValidationError):
        FormIntelligenceReport(status="completed", props={"raw": "record"})


def test_filler_report_records_rejections_and_refresh():
    report = FillerReport(
        status="partially_applied",
        applied=["hasSubsidiary"],
        rejected=[{"componentName": "ghost", "reason": "Unknown component."}],
        configurationRefreshed=True,
    )

    payload = report.model_dump(by_alias=True)
    assert payload["configurationRefreshed"] is True
    assert payload["rejected"] == [
        {"componentName": "ghost", "reason": "Unknown component."}
    ]
