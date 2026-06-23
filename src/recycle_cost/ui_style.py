from __future__ import annotations

import streamlit as st


def apply_layout_style() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.25rem;
            max-width: 1240px;
        }
        section[data-testid="stSidebar"] {
            border-right: 1px solid #d8e2ef;
        }
        div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
            border-color: #1c3d63;
            border-radius: 4px;
            background: #fbfdff;
            min-height: 138px;
        }
        div[data-testid="stMetric"] {
            border: 1px solid #d8e2ef;
            border-radius: 4px;
            padding: 0.75rem 0.85rem;
            background: #ffffff;
        }
        div[data-testid="stTabs"] button {
            font-weight: 600;
        }
        .stButton > button {
            border-radius: 4px;
            border-color: #1c3d63;
        }
        h1, h2, h3 {
            letter-spacing: 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
