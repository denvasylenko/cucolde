from adaptive_form_agent.form_intelligence import FormIntelligenceEngine
from adaptive_form_agent.form_intelligence.tools import FORM_INTELLIGENCE_TOOLS

JSX = """
<Form componentName="businessForm">
  <Section componentName="companySection" title="Company">
    <Accordion componentName="detailsAccordion" label="Details">
      <TextField componentName="companyName" label={dynamicLabel} />
      <Select componentName="country" />
    </Accordion>
  </Section>
</Form>
"""


def config(country_visible: bool = False) -> dict:
    return {
        "props": {
            "companyName": {
                "label": "Company name",
                "visible": True,
                "sensitive": True,
            },
            "country": {
                "label": "Country of registration",
                "visible": country_visible,
            },
        },
        "state": {"companyName": "Secret Corp", "country": "UA"},
        "actions": [{"componentName": "companyName", "event": "onChange"}],
        "events": {},
    }


def engine() -> FormIntelligenceEngine:
    return FormIntelligenceEngine(JSX, config())


def test_search_uses_component_labels_and_names():
    result = engine().search_components("country registration")
    assert result["matches"][0]["componentName"] == "country"


def test_inspection_is_explicit_and_redacts_sensitive_state():
    result = engine().inspect_component("companyName")
    component = result["component"]

    assert result["found"] is True
    assert component["parent"] == "detailsAccordion"
    assert component["label"] == "Company name"
    assert component["visibility"] == "visible"
    assert component["onChangeConfigured"] is True
    assert component["currentState"] is None
    assert component["hasState"] is False
    assert any("Dynamic JSX attribute" in item for item in result["warnings"])
    assert any("Sensitive current state" in item for item in result["warnings"])


def test_unknown_visibility_and_missing_components_are_reported():
    section = engine().inspect_component("companySection")
    assert section["component"]["visibility"] == "unknown"
    assert section["component"]["onChangeConfigured"] is False

    missing = engine().inspect_component("missing")
    assert missing["found"] is False
    assert missing["warnings"]


def test_navigation_uses_jsx_parent_chain():
    result = engine().get_navigation_path("country")
    assert [item["componentName"] for item in result["path"]] == [
        "businessForm",
        "companySection",
        "detailsAccordion",
        "country",
    ]


def test_config_update_does_not_reparse_jsx():
    instance = engine()
    components = instance.components
    instance.update_config(config(country_visible=True))

    assert instance.components is components
    assert instance.inspect_component("country")["component"]["visibility"] == "visible"


def test_exactly_three_tools_are_exposed_without_runtime_in_the_llm_schema():
    assert [tool.name for tool in FORM_INTELLIGENCE_TOOLS] == [
        "search_components",
        "inspect_component",
        "get_navigation_path",
    ]
    for intelligence_tool in FORM_INTELLIGENCE_TOOLS:
        properties = intelligence_tool.tool_call_schema.model_json_schema()["properties"]
        assert "runtime" not in properties
