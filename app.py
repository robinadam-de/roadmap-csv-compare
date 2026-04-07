import pandas as pd
import streamlit as st

st.set_page_config(page_title="Roadmap CSV Vergleich", layout="wide")
st.title("Roadmap CSV Vergleich")
st.write("Lade zwei Advanced-Roadmaps-CSV-Dateien hoch und zeige nur geänderte Zieltermine an.")

old_file = st.file_uploader("Alte CSV", type="csv")
new_file = st.file_uploader("Neue CSV", type="csv")

DATE_COLS = ["Zielstartdatum", "Zielenddatum"]
KEY_COL = "Vorgangsschlüssel"
TITLE_COL = "Titel"

def prepare_df(file):
    df = pd.read_csv(file)

    for col in DATE_COLS:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format="%d/%b/%y", errors="coerce")

    return df

if old_file and new_file:
    try:
        old = prepare_df(old_file)
        new = prepare_df(new_file)

        required_cols = [KEY_COL, TITLE_COL, "Zielstartdatum", "Zielenddatum"]
        missing_old = [c for c in required_cols if c not in old.columns]
        missing_new = [c for c in required_cols if c not in new.columns]

        if missing_old or missing_new:
            st.error(
                f"Fehlende Spalten. "
                f"Alt fehlt: {missing_old if missing_old else 'keine'} | "
                f"Neu fehlt: {missing_new if missing_new else 'keine'}"
            )
        else:
            merged = old.merge(new, on=KEY_COL, suffixes=("_old", "_new"))

            dummy_date = pd.Timestamp("1900-01-01")

            start_changed = (
                merged["Zielstartdatum_old"].fillna(dummy_date) !=
                merged["Zielstartdatum_new"].fillna(dummy_date)
            )

            end_changed = (
                merged["Zielenddatum_old"].fillna(dummy_date) !=
                merged["Zielenddatum_new"].fillna(dummy_date)
            )

            changes = merged[start_changed | end_changed].copy()

            changes["Start_Delta_Tage"] = (
                changes["Zielstartdatum_new"] - changes["Zielstartdatum_old"]
            ).dt.days

            changes["End_Delta_Tage"] = (
                changes["Zielenddatum_new"] - changes["Zielenddatum_old"]
            ).dt.days

            changes["Dauer_alt"] = (
                changes["Zielenddatum_old"] - changes["Zielstartdatum_old"]
            ).dt.days + 1

            changes["Dauer_neu"] = (
                changes["Zielenddatum_new"] - changes["Zielstartdatum_new"]
            ).dt.days + 1

            result = changes[[
                "Vorgangsschlüssel",
                "Titel_old",
                "Zielstartdatum_old", "Zielenddatum_old", "Dauer_alt",
                "Zielstartdatum_new", "Zielenddatum_new", "Dauer_neu",
                "Start_Delta_Tage",
                "End_Delta_Tage"
            ]].copy()

            result = result.rename(columns={
                "Titel_old": "Titel",
                "Zielstartdatum_old": "Zielstart_alt",
                "Zielstartdatum_new": "Zielstart_neu",
                "Zielenddatum_old": "Zielende_alt",
                "Zielenddatum_new": "Zielende_neu",
            })

            for col in ["Zielstart_alt", "Zielstart_neu", "Zielende_alt", "Zielende_neu"]:
                result[col] = result[col].dt.strftime("%Y-%m-%d")
                result[col] = result[col].fillna("")

            st.success(f"{len(result)} geänderte Vorgänge gefunden")
            st.dataframe(result, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Fehler beim Verarbeiten der Dateien: {e}")
else:
    st.info("Bitte beide CSV-Dateien hochladen.")
