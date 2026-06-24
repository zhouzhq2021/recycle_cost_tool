from recycle_cost.i18n import TEXT
from recycle_cost import ui_pages


def test_recycling_flow_cards_switch_between_legacy_and_new_hydro(monkeypatch):
    monkeypatch.setitem(ui_pages.st.session_state, "recycling_flow_variant", "old")
    legacy_cards = ui_pages._recycling_flow_cards("Hydro", TEXT["zh"])
    legacy_titles = [card[0] for card in legacy_cards]
    assert "Disassembly" in legacy_titles
    assert "Preproc. Par." in legacy_titles
    assert TEXT["zh"]["lithium_extraction"] not in legacy_titles

    monkeypatch.setitem(ui_pages.st.session_state, "recycling_flow_variant", "new")
    new_cards = ui_pages._recycling_flow_cards("Hydro", TEXT["zh"])
    new_titles = [card[0] for card in new_cards]
    assert new_cards[0][:3] == (
        TEXT["zh"]["new_preprocessing"],
        TEXT["zh"]["new_preprocessing_desc"],
        "recycling_new_preprocessing",
    )
    assert new_cards[0][3] == "new_preprocessing"
    assert TEXT["zh"]["lithium_extraction"] in new_titles
    assert any(card[0] == TEXT["zh"]["lithium_extraction"] and card[3] == "lithium_extraction" for card in new_cards)
    assert "Disassembly" not in new_titles
    assert "Preproc. Par." not in new_titles


def test_recycling_flow_cards_switch_to_new_direct_route(monkeypatch):
    monkeypatch.setitem(ui_pages.st.session_state, "recycling_flow_variant", "new")

    cards = ui_pages._recycling_flow_cards("Direct", TEXT["zh"])
    titles = [card[0] for card in cards]

    assert cards[0][0] == TEXT["zh"]["new_preprocessing"]
    assert cards[0][2] == "recycling_new_preprocessing"
    assert cards[0][3] == "new_preprocessing"
    assert TEXT["zh"]["direct_molten_salt"] in titles
    assert TEXT["zh"]["direct_chemical_etching"] in titles
    assert any(card[0] == TEXT["zh"]["direct_molten_salt"] and card[3] == "direct_molten_salt" for card in cards)


def test_new_flow_copy_matches_secondary_development_model_scope():
    assert "无依据的硬编码假设" in TEXT["zh"]["new_flow_calculation_note"]
    assert "用户填写完整后才能计算" in TEXT["zh"]["new_flow_calculation_note"]
    assert "does not use unsupported hard-coded assumptions" in TEXT["en"]["new_flow_calculation_note"]
    assert "drag" not in TEXT["en"]["custom_flow_hint"].casefold()
    assert "拖" not in TEXT["zh"]["custom_flow_hint"]
    assert "旧预处理黑粉逻辑" in TEXT["zh"]["legacy_preprocessing_required"]
    assert "不会执行新流程计算" in TEXT["zh"]["shared_module_model_note"]
    assert "will not run until user-supplied new-flow parameters are complete" in TEXT["en"]["shared_module_model_note"]


def test_branch_setup_status_rows_flag_required_recycling_inputs():
    values = {
        "feedstock_chemistry": "NMC(622)",
        "feedstock_type": "Select Type",
        "feedstock_tonnes_per_year": 0.0,
        "recycling_process": "Select Process",
    }

    rows = ui_pages._branch_setup_status_rows("recycling", values, TEXT["zh"])
    status_by_item = {row[TEXT["zh"]["setup_item"]]: row[TEXT["zh"]["setup_status"]] for row in rows}

    assert status_by_item[TEXT["zh"]["feedstock_chemistry"]] == TEXT["zh"]["setup_ready"]
    assert status_by_item[TEXT["zh"]["feedstock_type"]] == TEXT["zh"]["setup_review"]
    assert status_by_item[TEXT["zh"]["feedstock_tonnes"]] == TEXT["zh"]["setup_review"]
    assert status_by_item[TEXT["zh"]["recycling_process"]] == TEXT["zh"]["setup_review"]


def test_branch_setup_status_rows_cover_production_inputs():
    values = {
        "manufacturing_chemistry": "NMC(811)",
        "cathode_chemistry": "NMC(811)",
        "throughput_gwh_per_year": 50.0,
        "cathode_throughput_gwh_per_year": 0.0,
    }

    rows = ui_pages._branch_setup_status_rows("production", values, TEXT["zh"])

    assert {row[TEXT["zh"]["setup_status"]] for row in rows} == {TEXT["zh"]["setup_ready"]}
