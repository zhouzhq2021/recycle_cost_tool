from recycle_cost import ui_sidebar


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
