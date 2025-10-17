# -*- coding: utf-8 -*-
# Telemarketing Analysis (Streamlit) — updated for Streamlit >= 1.30
# - Replaced deprecated @st.cache with @st.cache_data
# - Fixed Excel writer usage
# - Made images optional (won't crash if files are missing)
# - Safer handling when filters return empty data
# - Minor layout/labeling tweaks
#
# Run with: streamlit run app_7_streamlit_fixed.py

import pandas as pd
import streamlit as st
import seaborn as sns
import matplotlib.pyplot as plt
from PIL import Image
from io import BytesIO

# Must be the first Streamlit call
st.set_page_config(
    page_title="Telemarketing analysis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Visual style
custom_params = {"axes.spines.right": False, "axes.spines.top": False}
sns.set_theme(style="ticks", rc=custom_params)

# ---------- Data helpers ----------
@st.cache_data(show_spinner=True)
def load_data(file_data):
    """Try CSV (sep=';') then Excel."""
    try:
        return pd.read_csv(file_data, sep=";")
    except Exception:
        file_data.seek(0)
        return pd.read_excel(file_data)

@st.cache_data
def multiselect_filter(relatorio, col, selecionados):
    if "all" in selecionados:
        return relatorio
    return relatorio[relatorio[col].isin(selecionados)].reset_index(drop=True)

@st.cache_data
def convert_df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")

@st.cache_data
def to_excel_bytes(df: pd.DataFrame) -> bytes:
    output = BytesIO()
    # Use a context manager; no writer.save() needed
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
    return output.getvalue()

def safe_sidebar_image(path: str, caption: str | None = None):
    try:
        st.sidebar.image(Image.open(path), caption=caption, use_container_width=True)
    except Exception:
        pass  # If the image file doesn't exist, just ignore

# ---------- App ----------
def main():
    # Header
    st.title("Telemarketing analysis")
    st.markdown("---")

    # Optional images (won't crash if files are missing)
    safe_sidebar_image("Bank-Branding.jpg")
    # If you have a local PNG icon you want to use instead of the emoji:
    # safe_sidebar_image("telmarketing_icon.png")

    # File upload
    st.sidebar.write("## Suba o arquivo")
    data_file_1 = st.sidebar.file_uploader("Bank marketing data", type=["csv", "xlsx"])

    if data_file_1 is None:
        st.info("👉 Carregue um arquivo `.csv` (separado por `;`) ou `.xlsx` na barra lateral.")
        return

    # Load
    bank_raw = load_data(data_file_1)
    bank = bank_raw.copy()

    # Basic checks
    required_cols = [
        "age","job","marital","default","housing","loan",
        "contact","month","day_of_week","y"
    ]
    missing = [c for c in required_cols if c not in bank.columns]
    if missing:
        st.error(f"As colunas obrigatórias não foram encontradas: {missing}")
        st.stop()

    # Before filters
    st.write("## Antes dos filtros")
    st.dataframe(bank_raw.head(50), use_container_width=True)

    # Sidebar filters
    with st.sidebar.form(key="filters"):
        graph_type = st.radio("Tipo de gráfico:", ("Barras", "Pizza"))

        max_age = int(bank["age"].max())
        min_age = int(bank["age"].min())
        idades = st.slider(
            label="Idade",
            min_value=min_age,
            max_value=max_age,
            value=(min_age, max_age),
            step=1,
        )

        def plus_all(unique_list):
            xs = sorted([x for x in unique_list if pd.notna(x)])
            xs.append("all")
            return xs

        jobs_selected       = st.multiselect("Profissão",         plus_all(bank["job"].unique().tolist()),       ["all"])
        marital_selected    = st.multiselect("Estado civil",      plus_all(bank["marital"].unique().tolist()),   ["all"])
        default_selected    = st.multiselect("Default",           plus_all(bank["default"].unique().tolist()),   ["all"])
        housing_selected    = st.multiselect("Tem financiamento imob?", plus_all(bank["housing"].unique().tolist()), ["all"])
        loan_selected       = st.multiselect("Tem empréstimo?",   plus_all(bank["loan"].unique().tolist()),      ["all"])
        contact_selected    = st.multiselect("Meio de contato",   plus_all(bank["contact"].unique().tolist()),   ["all"])
        month_selected      = st.multiselect("Mês do contato",    plus_all(bank["month"].unique().tolist()),     ["all"])
        day_of_week_selected= st.multiselect("Dia da semana",     plus_all(bank["day_of_week"].unique().tolist()),["all"])

        submit_button = st.form_submit_button(label="Aplicar")

    # Apply filters
    bank = (
        bank.query("age >= @idades[0] and age <= @idades[1]")
            .pipe(multiselect_filter, "job",         jobs_selected)
            .pipe(multiselect_filter, "marital",     marital_selected)
            .pipe(multiselect_filter, "default",     default_selected)
            .pipe(multiselect_filter, "housing",     housing_selected)
            .pipe(multiselect_filter, "loan",        loan_selected)
            .pipe(multiselect_filter, "contact",     contact_selected)
            .pipe(multiselect_filter, "month",       month_selected)
            .pipe(multiselect_filter, "day_of_week", day_of_week_selected)
    )

    # After filters
    st.write("## Após os filtros")
    if bank.empty:
        st.warning("Nenhuma linha corresponde aos filtros aplicados. Ajuste os filtros e tente novamente.")
        # Ainda assim mostra a proporção original abaixo
    else:
        st.dataframe(bank.head(50), use_container_width=True)

    # Target proportions (original vs filtered)
    st.markdown("---")
    st.write("## Proporção de aceite (y = yes/no)")

    bank_raw_target_perc = (bank_raw["y"].value_counts(normalize=True).sort_index() * 100).to_frame(name="y")
    if bank.empty:
        bank_target_perc = bank_raw_target_perc.copy()
        st.info("Usando a proporção **original** porque o conjunto filtrado ficou vazio.")
    else:
        bank_target_perc = (bank["y"].value_counts(normalize=True).sort_index() * 100).to_frame(name="y")

    # Download tables
    col1, col2 = st.columns(2)
    with col1:
        st.write("### Proporção original")
        st.dataframe(bank_raw_target_perc, use_container_width=True)
        col1.download_button(
            label="📥 Download",
            data=to_excel_bytes(bank_raw_target_perc),
            file_name="bank_raw_y.xlsx",
        )
    with col2:
        st.write("### Proporção da tabela com filtros")
        st.dataframe(bank_target_perc, use_container_width=True)
        col2.download_button(
            label="📥 Download",
            data=to_excel_bytes(bank_target_perc),
            file_name="bank_y.xlsx",
        )

    # Plots
    fig, ax = plt.subplots(1, 2, figsize=(8, 3.8))

    if graph_type == "Barras":
        sns.barplot(x=bank_raw_target_perc.index, y="y", data=bank_raw_target_perc, ax=ax[0])
        ax[0].set_title("Dados brutos", fontweight="bold")
        try:
            ax[0].bar_label(ax[0].containers[0], fmt="%.2f")
        except Exception:
            pass

        sns.barplot(x=bank_target_perc.index, y="y", data=bank_target_perc, ax=ax[1])
        ax[1].set_title("Dados filtrados", fontweight="bold")
        try:
            ax[1].bar_label(ax[1].containers[0], fmt="%.2f")
        except Exception:
            pass
    else:
        bank_raw_target_perc.plot(kind="pie", autopct="%.2f", y="y", ax=ax[0], legend=False)
        ax[0].set_title("Dados brutos", fontweight="bold")

        bank_target_perc.plot(kind="pie", autopct="%.2f", y="y", ax=ax[1], legend=False)
        ax[1].set_title("Dados filtrados", fontweight="bold")

    st.pyplot(fig)
    st.caption("Dica: use os botões na barra lateral para ajustar os filtros e exportar os resultados.")

if __name__ == "__main__":
    main()
