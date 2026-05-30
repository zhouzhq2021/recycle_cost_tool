from __future__ import annotations

import streamlit as st

from recycle_cost.extractors import available_reference_tables
from recycle_cost.model import default_scenario, scenario_options
from recycle_cost.ui_pages import render_app_pages
from recycle_cost.ui_sidebar import render_sidebar


st.set_page_config(
    page_title="EverBatt Replica",
    page_icon="",
    layout="wide",
)


@st.cache_data(show_spinner=False)
def cached_default_scenario():
    return default_scenario()


@st.cache_data(show_spinner=False)
def cached_scenario_options():
    return scenario_options()


@st.cache_data(show_spinner=False)
def cached_reference_tables():
    return available_reference_tables()


default_base = cached_default_scenario()
options = cached_scenario_options()

sidebar = render_sidebar(default_base, options)
render_app_pages(sidebar.scenario, sidebar.process, sidebar.text, cached_reference_tables())
