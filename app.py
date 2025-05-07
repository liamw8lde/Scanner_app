#!/usr/bin/env python3
"""
app.py

Streamlit app to link 125 kHz UID into a member CSV on disk.
Reads 'members.csv' (semicolon-separated) with columns:
Vorname, Nachname, E-Mail, Transponder, etc.

1. Combines Vorname + Nachname into a Name searchable dropdown.
2. Verify member’s E-Mail.
3. Scan card over serial (FS-2044) to read UID.
4. Overwrite 'members.csv' with updated Transponder column.
"""
import streamlit as st
import pandas as pd
import os
import serial
import serial.tools.list_ports

# 1) Page config must come first
st.set_page_config(page_title="Mitglieder-Kartenlinker", layout="centered")

# 2) Inject CSS to fix display quirks
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
BAUD_RATE     = 9600
LOGO_URL      = (
    "https://image.jimcdn.com/app/cms/image/transf/dimension%3D152x10000"
    ":format%3Dpng/path/s65ba28b2b3a08779/image/"
    "i23bf4860d606df32/version/1454087215/image.png"
)

# 4) Auto-detect serial port for FS-2044 reader (Windows or Linux)
def find_reader_port():
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        desc = (p.description or '').lower()
        hwid = (p.hwid or '').lower()
        # match easyident or fs-2044 or generic USB serial
        if 'easyident' in desc or 'fs-2044' in desc or 'usb serial' in desc or 'ttyusb' in p.device.lower():
            return p.device
    # fallback Linux default
    if os.name == 'posix':
        return '/dev/ttyUSB0'
    # fallback Windows default
    return 'COM6'

SERIAL_PORT = find_reader_port()

# 5) Session state for last-read UID
if 'uid' not in st.session_state:
    st.session_state.uid = ''

# 6) Header with logo and title
st.image(LOGO_URL, width=200)
st.title("Mitglieder-Kartenlinker")

# 7) Load CSV from disk
if not os.path.exists(CSV_FILENAME):
    st.error(f"Datei '{CSV_FILENAME}' nicht gefunden. Bitte im Arbeitsverzeichnis ablegen.")
    st.stop()

df = pd.read_csv(CSV_FILENAME, sep=';', dtype=str).fillna('')
if 'Transponder' not in df.columns:
    df['Transponder'] = ''
df['Name'] = df['Vorname'].str.strip() + ' ' + df['Nachname'].str.strip()

# 8) Name searchable dropdown (multiselect for filter)
all_names = df['Name'].tolist()
name_selection = st.multiselect(
    "1. Name suchen und wählen", all_names, max_selections=1, key='name_multiselect'
)
name = name_selection[0] if name_selection else None
if not name:
    st.info("Bitte einen Namen eingeben und auswählen.")
    st.stop()

# 9) Email verification
email = st.text_input("2. E-Mail zur Verifikation", key='email').strip().lower()
if st.button("Email prüfen"):
    member = df[df['Name'] == name]
    if not member.empty and member.iloc[0].get('E-Mail','').strip().lower() == email:
        st.success("Email verifiziert. Bitte Karte scannen.")
    else:
        st.error("Email stimmt nicht mit dem gewählten Mitglied überein.")

# 10) Scan card button
def scan_card():
    try:
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2) as ser:
            return ser.readline().decode('ascii', errors='ignore').strip()
    except Exception as e:
        st.error(f"Fehler beim Lesen der Karte auf {SERIAL_PORT}: {e}")
        return ''

if st.button(f"3. Karte scannen via {SERIAL_PORT}"):
    raw = scan_card()
    if raw:
        st.session_state.uid = raw
        st.success(f"Gelesene UID: {raw}")

# 11) UID input field
uid = st.text_input(
    "4. Kartenuid eingeben oder scannen",
    value=st.session_state.uid,
    key='uid_input'
).strip()

# 12) Save and update CSV
if st.button("5. UID speichern und Datei aktualisieren"):
    if uid:
        df.loc[df['Name'] == name, 'Transponder'] = uid
        df.to_csv(CSV_FILENAME, sep=';', index=False)
        st.success(f"UID {uid} gespeichert für {name}. Datei aktualisiert.")
    else:
        st.error("Keine UID vorhanden. Bitte Karte scannen oder manuell eingeben.")
