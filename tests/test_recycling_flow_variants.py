from recycle_cost.i18n import TEXT
from recycle_cost import ui_pages


def test_recycling_flow_cards_switch_between_legacy_and_new_hydro(monkeypatch):
    monkeypatch.setitem(ui_pages.st.session_state, "recycling_flow_variant", "old")
    legacy_cards = ui_pages._recycling_flow_cards("Hydro", TEXT["zh"])
    legacy_titles = [title for title, _, _ in legacy_cards]
    assert "Disassembly" in legacy_titles
    assert "Preproc. Par." in legacy_titles
    assert TEXT["zh"]["lithium_extraction"] not in legacy_titles

    monkeypatch.setitem(ui_pages.st.session_state, "recycling_flow_variant", "new")
    new_cards = ui_pages._recycling_flow_cards("Hydro", TEXT["zh"])
    new_titles = [title for title, _, _ in new_cards]
    assert new_cards[0] == (
        TEXT["zh"]["new_preprocessing"],
        TEXT["zh"]["new_preprocessing_desc"],
        "recycling_new_preprocessing",
    )
    assert TEXT["zh"]["lithium_extraction"] in new_titles
    assert "Disassembly" not in new_titles
    assert "Preproc. Par." not in new_titles


def test_recycling_flow_cards_switch_to_new_direct_route(monkeypatch):
    monkeypatch.setitem(ui_pages.st.session_state, "recycling_flow_variant", "new")

    cards = ui_pages._recycling_flow_cards("Direct", TEXT["zh"])
    titles = [title for title, _, _ in cards]

    assert cards[0][0] == TEXT["zh"]["new_preprocessing"]
    assert cards[0][2] == "recycling_new_preprocessing"
    assert TEXT["zh"]["direct_molten_salt"] in titles
    assert TEXT["zh"]["direct_chemical_etching"] in titles
