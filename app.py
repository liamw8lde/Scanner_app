#!/usr/bin/env python3
"""
app.py

Streamlit app to link 125 kHz UID into a member CSV on disk.
Reads 'members.csv' (semicolon-separated) with columns:
Vorname, Nachname, E-Mail, Transponder, etc.

1. Combines Vorname + Nachname into a Name search-and-select field (live filter).
2. Verify member’s E-Mail.
3. Scan card over serial (FS-2044 via COM6) to read UID.
4. Overwrite 'members.csv' with updated Transponder column.
"""

import streamlit as st
import pandas as pd
import os
import serial

# 1) Page config must be the first Streamlit call
st.set_page_config(page_title="Mitglieder-Kartenlinker", layout="centered")

# 2) Inject CSS to fix dropdown overlap if needed
st.markdown("""
<style>
[data-baseweb="select"] li {
  padding: 8px 12px !important;
  line-height: 1.5em !important;
  height: auto !important;
}
[data-baseweb="select"] ul {
  max-height: 300px !important;
}
</style>
""", unsafe_allow_html=True)

# 3) Configuration
CSV_FILENAME = 'members.csv'
SERIAL_PORT   = 'COM6'   # adjust as needed
BAUD_RATE     = 9600
LOGO_URL      = (
    "https://image.jimcdn.com/app/cms/image/transf/dimension%3D152x10000"
    ":format%3Dpng/path/s65ba28b2b3a08779/image/"
    "i23bf4860d606df32/version/1454087215/image.png"
)

# 4) Session state for last-read UID
if 'uid' not in st.session_state:
    st.session_state.uid = ''

# 5) Header with logo and title
st.image(LOGO_URL, width=200)
st.title("Mitglieder-Kartenlinker")

# 6) Load CSV from disk
if not os.path.exists(CSV_FILENAME):
    st.error(f"Datei '{CSV_FILENAME}' nicht gefunden. Bitte im Arbeitsverzeichnis ablegen.")
    st.stop()

df = pd.read_csv(CSV_FILENAME, sep=';', dtype=str).fillna('')
if 'Transponder' not in df.columns:
    df['Transponder'] = ''
df['Name'] = df['Vorname'].str.strip() + ' ' + df['Nachname'].str.strip()

# 7) Name search-and-select (live filter)
def _noop():
    """Dummy callback to force rerun on every keystroke."""
    pass

name_search = st.text_input(
    "1. Name suchen und wählen",
    key='name_search',
    on_change=_noop
).strip()

all_names = df['Name'].tolist()
filtered = [n for n in all_names if name_search.lower() in n.lower()] if name_search else []

if not name_search:
    st.info("Bitte Suchbegriff eingeben, um Namen zu filtern.")
    st.stop()
elif not filtered:
    st.warning("Keine Übereinstimmungen gefunden.")
    st.stop()
else:
    name = st.radio("Gefundene Namen", filtered, key='name_radio')

# 8) Once a name is selected, proceed
if name:
    # Email verification
    email = st.text_input("2. E-Mail zur Verifikation", key='email').strip().lower()
    if st.button("Email prüfen"):
        member = df[df['Name'] == name]
        if not member.empty and member.iloc[0].get('E-Mail','').strip().lower() == email:
            st.success("Email verifiziert. Bitte Karte scannen.")
        else:
            st.error("Email stimmt nicht mit dem gewählten Mitglied überein.")

    # Card scan button
    if st.button("3. Karte scannen via COM6"):
        try:
            with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2) as ser:
                raw = ser.readline().decode('ascii', errors='ignore').strip()
                st.session_state.uid = raw
                st.success(f"Gelesene UID: {raw}")
        except Exception as e:
            st.error(f"Fehler beim Lesen der Karte: {e}")

    # UID input field (editable)
    uid = st.text_input(
        "4. Kartenuid eingeben oder scannen",
        value=st.session_state.uid,
        key='uid_input'
    ).strip()

    # Save UID back to CSV
    if st.button("5. UID speichern und Datei aktualisieren"):
        if uid:
            df.loc[df['Name'] == name, 'Transponder'] = uid
            df.to_csv(CSV_FILENAME, sep=';', index=False)
            st.success(f"UID {uid} gespeichert für {name}. Datei aktualisiert.")
        else:
            st.error("Keine UID vorhanden. Bitte Karte scannen oder manuell eingeben.")
