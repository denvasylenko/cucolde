from adaptive_form_agent.form_intelligence import FormIntelligenceEngine
from adaptive_form_agent.form_intelligence.filling_tools import FILLING_TOOLS
from adaptive_form_agent.form_intelligence.jsx_index import parse_jsx
from adaptive_form_agent.form_intelligence.tools import FORM_INTELLIGENCE_TOOLS

from helpers import form_source


def engine(**options) -> FormIntelligenceEngine:
    source = form_source(**options)
    return FormIntelligenceEngine(source["jsx"], source["idfConfig"])


def test_search_returns_the_complete_flat_component():
    match = engine().search_components("country")["matches"][0]

    assert match["name"] == "subsidiaryCountry"
    assert match["tag"] == "Dropdown"
    assert match["path"] == (
        "subsidiaryForm",
        "companyDetails",
        "subsidiaryDetails",
        "subsidiaryCountry",
    )
    assert match["props"]["visible"] is False
    assert match["has_value"] is False


def test_sensitive_state_is_redacted_but_presence_is_kept():
    component = engine().get_component("companyName")

    assert component["state"] is None
    assert component["has_value"] is True
    assert component["on_change"] is False


def test_get_component_uses_exact_component_name():
    instance = engine()

    assert instance.get_component("hasSubsidiary")["on_change"] is True
    assert instance.get_component("missing") is None


def test_config_update_does_not_reparse_jsx():
    instance = engine()
    jsx_index = instance.jsx_index
    source = form_source(subsidiary_visible=True)
    instance.update_config(source["idfConfig"])

    assert instance.jsx_index is jsx_index
    assert instance.get_component("subsidiaryName")["props"]["visible"] is True


def test_jsx_parsing_is_cached_per_source():
    source = form_source()

    assert parse_jsx(source["jsx"]) is parse_jsx(source["jsx"])


def test_find_actions_filters_by_event_and_field_scope():
    instance = engine()

    partial = instance.find_actions(event="onPartialSubmit")["actions"]
    assert [a["trigger"]["name"] for a in partial] == ["saveCompany", "saveSubsidiary"]

    by_field = instance.find_actions(component_names=["parentCompany"])["actions"]
    assert [a["trigger"]["name"] for a in by_field] == ["saveSubsidiary"]
    assert by_field[0]["collect"] == [
        "subsidiaryName",
        "subsidiaryCountry",
        "parentCompany",
    ]

    by_trigger = instance.find_actions(component_names=["saveCompany"])["actions"]
    assert [a["event"] for a in by_trigger] == ["onPartialSubmit"]
    assert by_trigger[0]["trigger"]["path"][-1] == "saveCompany"
    assert by_trigger[0]["trigger"]["label"] == "Save company details"


def test_find_actions_reports_only_visible_enabled_required_gaps():
    hidden_scope = engine().find_actions(component_names=["saveSubsidiary"])
    assert hidden_scope["actions"][0]["missing_required"] == []

    shown = engine(subsidiary_visible=True).find_actions(
        component_names=["saveSubsidiary"]
    )["actions"][0]
    assert shown["missing_required"] == ["subsidiaryName", "subsidiaryCountry"]

    filled = engine(
        subsidiary_visible=True, subsidiary_name="Acme UK"
    ).find_actions(component_names=["saveSubsidiary"])["actions"][0]
    assert filled["missing_required"] == ["subsidiaryCountry"]


def test_find_actions_counts_explicit_errors_and_never_reports_readiness():
    source = form_source(subsidiary_visible=True, subsidiary_name="Acme UK")
    source["idfConfig"]["props"]["subsidiaryName"]["errors"] = ["Invalid name"]
    instance = FormIntelligenceEngine(source["jsx"], source["idfConfig"])

    action = instance.find_actions(component_names=["saveSubsidiary"])["actions"][0]

    assert action["with_errors"] == ["subsidiaryName"]
    assert "ready" not in action


def test_tools_are_split_by_specialist():
    assert [tool.name for tool in FORM_INTELLIGENCE_TOOLS] == [
        "search_components",
        "get_component",
        "find_actions",
    ]
    assert [tool.name for tool in FILLING_TOOLS] == [
        "get_dropdown_options",
        "search_input_options",
        "set_form_state",
    ]
    for tool in [*FORM_INTELLIGENCE_TOOLS, *FILLING_TOOLS]:
        properties = tool.tool_call_schema.model_json_schema()["properties"]
        assert "runtime" not in properties
        assert "revision" not in " ".join(properties).lower()
