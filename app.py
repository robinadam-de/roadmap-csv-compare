import pandas as pd
import streamlit as st

st.set_page_config(page_title="Roadmap CSV Vergleich", layout="wide")
st.title("Roadmap CSV Vergleich")
st.write("Lade zwei Advanced-Roadmaps-CSV-Dateien hoch und zeige nur geänderte Zieltermine an.")

old_file = st.file_uploader("Alte CSV", type="csv")
new_file = st.file_uploader("Neue CSV", type="csv")

# Konstanten für Spaltennamen und Formate
DATE_COLS = ["Zielstartdatum", "Zielenddatum"]
DATE_FORMAT = "%d/%b/%y"
DATE_OUTPUT_FORMAT = "%Y-%m-%d"
DUMMY_DATE = pd.Timestamp("1900-01-01")
KEY_COL = "Vorgangsschlüssel"
TITLE_COL = "Titel"
HIERARCHY_COL = "Hierachie"
ASSIGNEE_COL = "Zugewiesene Person"
STATUS_COL = "Vorgangsstatus"

REQUIRED_COLS = [KEY_COL, TITLE_COL, HIERARCHY_COL, ASSIGNEE_COL, STATUS_COL, "Zielstartdatum", "Zielenddatum"]
INT_COLS = ["Start_Delta_Tage", "End_Delta_Tage", "Dauer_alt", "Dauer_neu"]
DATE_OUTPUT_COLS = ["Zielstart_alt", "Zielstart_neu", "Zielende_alt", "Zielende_neu"]


def prepare_df(file):
    """Liest CSV und konvertiert Datumsspalten."""
    df = pd.read_csv(file)
    
    if df.empty:
        raise ValueError("CSV-Datei ist leer")

    for col in DATE_COLS:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format=DATE_FORMAT, errors="coerce")

    return df


def validate_dataframes(old, new):
    """Prüft ob beide DataFrames die erforderlichen Spalten haben."""
    missing_old = [c for c in REQUIRED_COLS if c not in old.columns]
    missing_new = [c for c in REQUIRED_COLS if c not in new.columns]
    
    if missing_old or missing_new:
        error_msg = (
            f"Fehlende Spalten. "
            f"Alt fehlt: {missing_old if missing_old else 'keine'} | "
            f"Neu fehlt: {missing_new if missing_new else 'keine'}"
        )
        st.error(error_msg)
        return False
    
    return True


def merge_and_filter_changes(old, new):
    """Merged DataFrames und filtert nur geänderte Zeilen."""
    # Nur notwendige Spalten vor dem Merge behalten
    merge_cols = [KEY_COL] + DATE_COLS + [TITLE_COL, HIERARCHY_COL, ASSIGNEE_COL, STATUS_COL]
    old_selected = old[[c for c in merge_cols if c in old.columns]].copy()
    new_selected = new[[c for c in merge_cols if c in new.columns]].copy()
    
    merged = old_selected.merge(new_selected, on=KEY_COL, suffixes=("_old", "_new"))

    start_changed = (
        merged["Zielstartdatum_old"].fillna(DUMMY_DATE) !=
        merged["Zielstartdatum_new"].fillna(DUMMY_DATE)
    )

    end_changed = (
        merged["Zielenddatum_old"].fillna(DUMMY_DATE) !=
        merged["Zielenddatum_new"].fillna(DUMMY_DATE)
    )

    changes = merged[start_changed | end_changed].copy()
    
    if changes.empty:
        return None
    
    return changes


def calculate_deltas(changes):
    """Berechnet die Zeitdifferenzen und Dauern."""
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

    return changes


def format_result(changes):
    """Formatiert das Resultat mit richtigen Spaltennamen."""
    result_cols = [
        KEY_COL,
        "Titel_old",
        f"{ASSIGNEE_COL}_old",
        f"{STATUS_COL}_old",
        f"{STATUS_COL}_new",
        f"{HIERARCHY_COL}_old",
        "Zielstartdatum_old",
        "Zielenddatum_old",
        "Zielstartdatum_new",
        "Zielenddatum_new",
        "Start_Delta_Tage",
        "End_Delta_Tage",
        "Dauer_alt",
        "Dauer_neu"
    ]
    
    result = changes[result_cols].copy()

    result = result.rename(columns={
        "Titel_old": "Titel",
        f"{ASSIGNEE_COL}_old": ASSIGNEE_COL,
        f"{STATUS_COL}_old": "Status_alt",
        f"{STATUS_COL}_new": "Status_neu",
        f"{HIERARCHY_COL}_old": HIERARCHY_COL,
        "Zielstartdatum_old": "Zielstart_alt",
        "Zielstartdatum_new": "Zielstart_neu",
        "Zielenddatum_old": "Zielende_alt",
        "Zielenddatum_new": "Zielende_neu",
    })

    # Konvertiere Integer-Spalten
    for col in INT_COLS:
        result[col] = result[col].astype("Int64")

    return result


def filter_initiatives(result):
    """Filtert nur Initiativen wenn Toggle aktiv ist."""
    only_initiatives = st.toggle("Nur Initiativen anzeigen", value=False)

    if only_initiatives:
        result = result[
            result[HIERARCHY_COL].astype(str).str.strip().str.lower() == "initiative"
        ].copy()

    return result


def highlight_duration(row):
    """Hebt Dauer-Änderungen farblich hervor und markiert Delta-Zellen."""
    styles = [""] * len(row)

    # Indizes für Spalten finden
    idx_alt = row.index.get_loc("Dauer_alt")
    idx_neu = row.index.get_loc("Dauer_neu")

    # Indizes für Delta-Spalten
    idx_start_delta = row.index.get_loc("Start_Delta_Tage")
    idx_end_delta = row.index.get_loc("End_Delta_Tage")

    dauer_alt = row["Dauer_alt"]
    dauer_neu = row["Dauer_neu"]

    # Dauer-Färbung wie vorher
    if pd.notna(dauer_alt) and pd.notna(dauer_neu):
        if dauer_neu <= dauer_alt:
            styles[idx_alt] = "background-color: #d4edda"
            styles[idx_neu] = "background-color: #d4edda"
        else:
            styles[idx_alt] = "background-color: #f8d7da"
            styles[idx_neu] = "background-color: #f8d7da"

    elif pd.notna(dauer_alt) and pd.isna(dauer_neu):
        styles[idx_neu] = "background-color: #f8d7da"

    # Delta-Färbung: >0 = rot, <0 = grün, ==0 = keine Farbe
    start_delta = row["Start_Delta_Tage"]
    end_delta = row["End_Delta_Tage"]

    if pd.notna(start_delta):
        try:
            sd = int(start_delta)
            if sd > 0:
                styles[idx_start_delta] = "background-color: #f8d7da"
            elif sd < 0:
                styles[idx_start_delta] = "background-color: #d4edda"
        except Exception:
            pass

    if pd.notna(end_delta):
        try:
            ed = int(end_delta)
            if ed > 0:
                styles[idx_end_delta] = "background-color: #f8d7da"
            elif ed < 0:
                styles[idx_end_delta] = "background-color: #d4edda"
        except Exception:
            pass

    return styles


def format_dates_for_display(result):
    """Konvertiert Datumspalten zu String-Format für Anzeige."""
    for col in DATE_OUTPUT_COLS:
        result[col] = pd.to_datetime(result[col], errors="coerce").dt.strftime(DATE_OUTPUT_FORMAT)
        result[col] = result[col].fillna("")

    return result


if old_file and new_file:
    try:
        old = prepare_df(old_file)
        new = prepare_df(new_file)

        if not validate_dataframes(old, new):
            st.stop()
        
        changes = merge_and_filter_changes(old, new)
        
        if changes is None or changes.empty:
            st.warning("Keine Änderungen in den Zieldaten gefunden.")
        else:
            changes = calculate_deltas(changes)
            result = format_result(changes)
            result = filter_initiatives(result)
            
            if not result.empty:
                result = format_dates_for_display(result)

                styled_result = (
                    result.drop(columns=[HIERARCHY_COL]).style
                    .apply(highlight_duration, axis=1)
                    .format({
                        "Start_Delta_Tage": lambda x: "" if pd.isna(x) else f"{int(x)}",
                        "End_Delta_Tage": lambda x: "" if pd.isna(x) else f"{int(x)}",
                        "Dauer_alt": lambda x: "" if pd.isna(x) else f"{int(x)}",
                        "Dauer_neu": lambda x: "" if pd.isna(x) else f"{int(x)}",
                    })
                )

                st.success(f"{len(result)} geänderte Vorgänge gefunden")
                st.dataframe(styled_result, use_container_width=True, hide_index=True)
            else:
                st.info("Nach Filterung keine Vorgänge vorhanden.")

    except Exception as e:
        st.error(f"Fehler beim Verarbeiten der Dateien: {e}")
else:
    st.info("Bitte beide CSV-Dateien hochladen.")
