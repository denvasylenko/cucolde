import pytest
from pydantic import ValidationError

from adaptive_form_agent.contracts import FormContext, SetFormStateRequest


def test_form_context_accepts_camel_case_wire_contract():
    context = FormContext.model_validate(
        {
            "contractVersion": "1.0",
            "formId": "subsidiary",
            "configRevision": 2,
            "fields": [
                {
                    "componentName": "hasSubsidiary",
                    "kind": "radio",
                    "label": "Has subsidiary?",
                }
            ],
            "layout": [],
        }
    )

    assert context.config_revision == 2
    assert context.model_dump(by_alias=True)["formId"] == "subsidiary"


def test_patch_requires_at_least_one_operation():
    with pytest.raises(ValidationError):
        SetFormStateRequest.model_validate(
            {"patches": [], "expectedRevision": 0}
        )
