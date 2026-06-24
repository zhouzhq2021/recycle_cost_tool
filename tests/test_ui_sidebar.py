from recycle_cost import ui_sidebar
from recycle_cost.model import default_scenario


def test_run_calculation_requires_selected_branch(monkeypatch):
    monkeypatch.setattr(ui_sidebar.st, "rerun", lambda: None)
    ui_sidebar.st.session_state.clear()
    ui_sidebar.st.session_state.branch = None
    ui_sidebar.st.session_state.calculation_done = True
    ui_sidebar.st.session_state.page = "home"

    ui_sidebar.run_calculation()

    assert ui_sidebar.st.session_state.calculation_done is False
    assert ui_sidebar.st.session_state.page == "branch_select"


def test_run_calculation_opens_results_for_selected_branch(monkeypatch):
    monkeypatch.setattr(ui_sidebar.st, "rerun", lambda: None)
    ui_sidebar.st.session_state.clear()
    ui_sidebar.st.session_state.branch = "production"
    ui_sidebar.st.session_state.calculation_done = False
    ui_sidebar.st.session_state.page = "branch_flow"

    ui_sidebar.run_calculation()

    assert ui_sidebar.st.session_state.calculation_done is True
    assert ui_sidebar.st.session_state.page == "results"


def test_set_page_replaces_module_focus(monkeypatch):
    monkeypatch.setattr(ui_sidebar.st, "rerun", lambda: None)
    ui_sidebar.st.session_state.clear()
    ui_sidebar.st.session_state.active_module_focus = "pack"

    ui_sidebar.set_page("module", module="production_manufacturing", module_focus="cell")
    assert ui_sidebar.st.session_state.active_module_focus == "cell"

    ui_sidebar.set_page("home")
    assert ui_sidebar.st.session_state.active_module_focus is None


def test_set_branch_clears_module_focus(monkeypatch):
    monkeypatch.setattr(ui_sidebar.st, "rerun", lambda: None)
    ui_sidebar.st.session_state.clear()
    ui_sidebar.st.session_state.active_module_focus = "direct_molten_salt"
    ui_sidebar.st.session_state.calculation_done = True

    ui_sidebar.set_branch("recycling")

    assert ui_sidebar.st.session_state.active_module_focus is None
    assert ui_sidebar.st.session_state.calculation_done is False
    assert ui_sidebar.st.session_state.page == "branch_parameters"


def test_run_calculation_blocks_incomplete_new_flow_parameters(monkeypatch):
    monkeypatch.setattr(ui_sidebar.st, "rerun", lambda: None)
    base = ui_sidebar.preset_values(default_scenario(), "pack_hydro")
    base["recycling_flow_variant"] = "new"
    ui_sidebar.st.session_state.clear()
    ui_sidebar.st.session_state.branch = "recycling"
    ui_sidebar.st.session_state.scenario_values = base
    ui_sidebar.st.session_state.calculation_done = False
    ui_sidebar.st.session_state.page = "branch_flow"

    ui_sidebar.run_calculation()

    assert ui_sidebar.st.session_state.calculation_done is False
    assert ui_sidebar.st.session_state.page == "branch_parameters"
    assert ui_sidebar.st.session_state.active_branch_parameter_section == "recycling_process"
