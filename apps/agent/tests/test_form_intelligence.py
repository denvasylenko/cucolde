from adaptive_form_agent.form_intelligence import FormIntelligenceEngine
from adaptive_form_agent.form_intelligence.tools import FORM_INTELLIGENCE_TOOLS

JSX = """
<Form componentName="businessForm">
  <Section componentName="companySection">
    <Accordion componentName="detailsAccordion">
      <TextField componentName={"companyName"} />
      <Select componentName="country" />
    </Accordion>
  </Section>
</Form>
"""


def config(country_visible: bool = False) -> dict:
    return {
        "props": {
            "businessForm": {"kind": "form", "label": "Business"},
            "companySection": {"kind": "section", "label": "Company"},
            "detailsAccordion": {"kind": "accordion", "label": "Details"},
            "companyName": {
                "kind": "text",
                "label": "Company name",
                "visible": True,
                "sensitive": True,
            },
            "country": {
                "kind": "dropdown",
                "label": "Country of registration",
                "visible": country_visible,
            },
        },
        "state": {"companyName": "Secret Corp", "country": "UA"},
        "actions": [{"componentName": "companyName", "event": "onChange"}],
        "events": {"onChange": {"companyName": True}},
    }


def engine() -> FormIntelligenceEngine:
    return FormIntelligenceEngine(JSX, config())


def test_search_returns_the_complete_flat_component():
    result = engine().search_components("country registration")
    match = result["matches"][0]

    assert match["name"] == "country"
    assert match["tag"] == "Select"
    assert match["path"] == (
        "businessForm",
        "companySection",
        "detailsAccordion",
        "country",
    )
    assert match["props"]["visible"] is False
    assert match["state"] == "UA"
    assert match["actions"] == ()
    assert match["on_change"] is False


def test_search_returns_actions_and_redacts_sensitive_state():
    result = engine().search_components("companyName")
    match = result["matches"][0]

    assert match["name"] == "companyName"
    assert match["state"] is None
    assert match["actions"] == (
        {"componentName": "companyName", "event": "onChange"},
    )
    assert match["on_change"] is True


def test_config_update_does_not_reparse_jsx():
    instance = engine()
    jsx_index = instance.jsx_index
    instance.update_config(config(country_visible=True))

    assert instance.jsx_index is jsx_index
    country = instance.search_components("country")["matches"][0]
    assert country["props"]["visible"] is True


def test_get_component_uses_exact_component_name():
    instance = engine()

    component = instance.get_component("country")

    assert component is not None
    assert component["name"] == "country"
    assert component["path"][-2:] == ("detailsAccordion", "country")
    assert instance.get_component("missing") is None


def test_search_and_get_component_are_exposed_to_the_agent():
    assert [tool.name for tool in FORM_INTELLIGENCE_TOOLS] == [
        "search_components",
        "get_component",
    ]
    for tool in FORM_INTELLIGENCE_TOOLS:
        properties = tool.tool_call_schema.model_json_schema()["properties"]
        assert "runtime" not in properties
