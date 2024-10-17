import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, timedelta
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Cartellino",
    page_icon=":clock1:",
    layout="wide"
)

st.header("Dashboard Cartellino", divider=True)

st.subheader("Dati giornalieri :calendar:")
st.text("I dati mostrati in questa tabella vengono letti da Google Drive. L'intervallo predefinito è una finestra di 15 giorni intorno alla data odierna (7 giorni prima e 7 giorni dopo)")

if 'date_from' not in st.session_state:
    # st.session_state.date_from = date.today() - timedelta(days=7)
    st.session_state.date_from = date(2025, 1, 1)
if 'date_to' not in st.session_state:
    # st.session_state.date_to = date.today() + timedelta(days=7)
    st.session_state.date_to = date(2025, 1, 31)

def validate_dates(date_from, date_to):
    if date_from >= date_to:
        st.error("La data 'A' deve essere maggiore della data 'Da'")
        st.stop()

# Acquisizione dati da Google Drive
# #################################
df = pd.read_csv("https://docs.google.com/spreadsheets/d/15HoJRe3AGq3VAgXN8gcO3cF0vfezPR6t0LvTc2R4WFo/export?format=csv&gid=896724717", parse_dates=['DATA'], date_format='%d/%m/%Y')

# Elaborazione dati di input
# #################################
# Converti la colonna 'DATA' in formato datetime, se non lo è già
df['DATA'] = pd.to_datetime(df['DATA'])


col_A, col_B = st.columns(2)

with col_A:
    date_from = st.date_input(label="Da", format="DD/MM/YYYY", key="date_from")
    # date_from = st.date_input(label="Da", value=date(2025, 1, 1), format="DD/MM/YYYY", key="date_from")

with col_B:
    date_to = st.date_input(label="A", format="DD/MM/YYYY", key="date_to")
    # date_to = st.date_input(label="A", value=date(2025, 1, 15), format="DD/MM/YYYY", key="date_to")

# Controlla la validità delle date
validate_dates(date_from, date_to)

# Filtra il DataFrame in base alle date
df = df[(df['DATA'] >= pd.to_datetime(st.session_state.date_from)) & (df['DATA'] <= pd.to_datetime(st.session_state.date_to))]

# Separa il giorno della settimana dalla data (lunedì = 0, domenica = 6)
df['SETTIMANA'] = df['DATA'].dt.isocalendar().week
# Calcolo del dovuto giornaliero in base alle condizioni
df['DOVUTO GIORNALIERO'] = pd.to_timedelta(0, unit='s')
df.loc[(df['TIPOLOGIA'] == 'SMART WORKING') | (df['TIPOLOGIA'] == 'PESCARA') | (df['TIPOLOGIA'] == 'TERAMO') | (df['TIPOLOGIA'] == 'MISSIONE'), 'DOVUTO GIORNALIERO'] = pd.to_timedelta(25920, unit='s')
df.loc[(df['TIPOLOGIA'] == 'PERMESSO') | (df['TIPOLOGIA'] == 'VISITA MEDICA') | (df['TIPOLOGIA'] == 'RECUPERO ORE RICERCATORI'), 'DOVUTO GIORNALIERO'] = pd.to_timedelta(25920, unit='s') - pd.to_timedelta(df['ORE RICHIESTE'], unit='h')

# Calcolo delle ore lavorate
def calcola_ore_lavorate(row):
    # Se 'ENTRATA_1' o 'USCITA_1' non sono valorizzate, ritorna NaT
    if pd.isna(row['ENTRATA_1']) or pd.isna(row['USCITA_1']):
        return pd.NaT
    # Calcolo ore lavorate tra 'ENTRATA_1' e 'USCITA_1'
    ore_lavorate = pd.to_datetime(row['USCITA_1'], format="%H:%M") - pd.to_datetime(row['ENTRATA_1'], format="%H:%M")
    # Se 'ENTRATA_2' e 'USCITA_2' sono valorizzate, somma anche queste
    if not pd.isna(row['ENTRATA_2']) and not pd.isna(row['USCITA_2']):
        ore_lavorate += pd.to_datetime(row['USCITA_2'], format="%H:%M") - pd.to_datetime(row['ENTRATA_2'], format="%H:%M")
    # Se 'PAUSA' è valorizzata, somma anche questa
    if not pd.isna(row['PAUSA']):
        ore_lavorate -= pd.to_timedelta(row['PAUSA']+':00')
    # Risultato
    return ore_lavorate

df.loc[(df['TIPOLOGIA'] == 'PERMESSO') | (df['TIPOLOGIA'] == 'VISITA MEDICA') | (df['TIPOLOGIA'] == 'RECUPERO ORE RICERCATORI'), 'ORE LAVORATE'] = pd.to_timedelta(0, unit='s')
df.loc[(df['TIPOLOGIA'] == 'SMART WORKING'), 'ORE LAVORATE'] = pd.to_timedelta(25920, unit='s') # 25920 è il valore in secondi di 7 ore e 12 minuti
df.loc[(df['TIPOLOGIA'] == 'PESCARA') | (df['TIPOLOGIA'] == 'TERAMO') | (df['TIPOLOGIA'] == 'MISSIONE') | (df['TIPOLOGIA'] == 'EVENTO'),'ORE LAVORATE'] = df.apply(calcola_ore_lavorate, axis=1)

# Calcolo saldo giornaliero
df['SALDO GIORNALIERO'] = df['ORE LAVORATE'] - df['DOVUTO GIORNALIERO']

# Funzione per formattare timedelta in ore e minuti, con segno
def format_saldo(row):
    if pd.isna(row):  # Se il valore è NaT, restituisci NaN
        return "-"
    # Calcola il totale in secondi
    total_seconds = row.total_seconds()
    # Determina se è negativo
    sign = "-" if total_seconds < 0 else ""
    # Prendi il valore assoluto per il calcolo delle ore e minuti
    abs_time = abs(total_seconds)
    # Converti in ore e minuti
    hours = int(abs_time // 3600)
    minutes = int((abs_time % 3600) // 60)
    # Restituisci il formato con segno
    return f"{sign}{hours}:{minutes:02d}"

df['SALDO_GIORNALIERO_FORMATTED'] = df['SALDO GIORNALIERO'].apply(format_saldo)
df['DOVUTO_GIORNALIERO_FORMATTED'] = df['DOVUTO GIORNALIERO'].apply(format_saldo)
df['ORE_LAVORATE_FORMATTED'] = df['ORE LAVORATE'].apply(format_saldo)

# Saldo generale 
# #########################
saldo_generale = df['SALDO GIORNALIERO'].sum()

# Saldo settimanale
# #########################
# Passo 1: Assicurati che la colonna 'DATA' sia di tipo datetime
df['DATA'] = pd.to_datetime(df['DATA'], dayfirst=True)
# Passo 2: Utilizza 'resample' per raggruppare per mese basato sulla data
df_settimanale = df.resample('W-SUN', on='DATA').sum()
df_settimanale['SETTIMANA'] = df_settimanale.index.isocalendar().week
df_settimanale['SALDO_SETT_FORMATTED'] = df_settimanale['SALDO GIORNALIERO'].apply(format_saldo)

# Saldo mensile
# #########################
# Passo 1: Assicurati che la colonna 'DATA' sia di tipo datetime
df['DATA'] = pd.to_datetime(df['DATA'], dayfirst=True)
# Passo 2: Utilizza 'resample' per raggruppare per mese basato sulla data
df_mensile = df.resample('ME', on='DATA').sum()
# Applica la funzione alla colonna dei saldi mensili
df_mensile['MESE'] = df_mensile.index.strftime('%b-%Y')
df_mensile['SALDO_MENSILE_FORMATTED'] = df_mensile['SALDO GIORNALIERO'].apply(format_saldo)

# DDF per visualizzazione tabella
ddf = df[['DATA', 'GIORNO', 'SETTIMANA', 'TIPOLOGIA', 'DETTAGLI', 'ORE RICHIESTE', 'ENTRATA_1', 'ENTRATA_2', 'USCITA_1', 'USCITA_2', 'PAUSA', 'DOVUTO_GIORNALIERO_FORMATTED', 'ORE_LAVORATE_FORMATTED','SALDO_GIORNALIERO_FORMATTED' ]].copy()
ddf['ORE RICHIESTE'] = pd.to_timedelta(ddf['ORE RICHIESTE'], unit='h')
ddf['ORE RICHIESTE'] = ddf['ORE RICHIESTE'].apply(format_saldo)

def row_color(row):
    w_color = 'background-color: lightsalmon; color: white;'
    f_color = 'background-color: crimson; color: white; font-weight: bold;'
    v_color = 'background-color: mediumseagreen; color: white; font-weight: bold;'
    p_color = 'background-color: olive; color: white; font-weight: bold;'
    # Applica il colore 
    if row['GIORNO'] in ['SAB', 'DOM']:
        return [w_color] * len(row)
    elif row['TIPOLOGIA'] == 'FESTIVITA':
        return [f_color] * len(row)
    elif row['TIPOLOGIA'] == 'FERIE':
        return [v_color] * len(row)
    elif row['TIPOLOGIA'] == 'PERMESSO' or row['TIPOLOGIA'] == 'VISITA MEDICA' or row['TIPOLOGIA'] == 'RECUPERO ORE RICERCATORI':
        return [p_color] * len(row)
    else:
        return [''] * len(row)

ddf.fillna('-', inplace=True)


# Streamlit app
# #################################

st.dataframe(
    ddf.style.apply(row_color, axis=1),
    column_config={
        "DATA": st.column_config.DateColumn(
            format="DD/MM/YYYY"
        ),
        "SALDO_GIORNALIERO_FORMATTED": st.column_config.Column(
            label="SALDO GIORNALIERO",    
        ),
        "DOVUTO_GIORNALIERO_FORMATTED": st.column_config.Column(
            label="DOVUTO GIORNALIERO",
        ),
        "ORE_LAVORATE_FORMATTED": st.column_config.Column(
            label="ORE LAVORATE",
        )
    }, 
    use_container_width=True, 
    hide_index=True
)

st.metric(
    label="Saldo Generale (hh:mm) nell'intervallo selezionato", 
    value=str(format_saldo(saldo_generale)).split(":")[0]+" ore e "+str(format_saldo(saldo_generale)).split(":")[1]+" minuti"
)

col1, col2 = st.columns(2)

with col1:

    st.subheader("Report settimanale :bookmark_tabs:")
    st.text("Questa sezione mostra il saldo aggregato per settimana")
    tab1, tab2 = st.tabs(["Grafico", "Dati"])
    
    with tab1:
        # Converti timedelta in ore decimali per la rappresentazione numerica
        df_settimanale['SALDO_GIORNALIERO_ORE'] = df_settimanale['SALDO GIORNALIERO'].dt.total_seconds() / 3600
        # Applica la funzione al saldo giornaliero per formattare le etichette
        df_settimanale['SALDO_GIORNALIERO_FORMATTED'] = df_settimanale['SALDO GIORNALIERO'].apply(format_saldo)
        # Crea una lista di colori in base ai valori positivi o negativi
        colors = ['mediumseagreen' if x >= 0 else 'firebrick' for x in df_settimanale['SALDO_GIORNALIERO_ORE']]        
        # Crea il grafico manualmente con go.Bar
        fig = go.Figure(data=[
            go.Bar(
                x=df_settimanale['SETTIMANA'],
                y=df_settimanale['SALDO_GIORNALIERO_ORE'],
                text=df_settimanale['SALDO_GIORNALIERO_FORMATTED'],
                textposition='outside',
                marker_color=colors  # Applica il colore condizionale
            )
        ])

        # Imposta il titolo del grafico
        fig.update_layout(
            # title_text='Saldo per settimana', 
            yaxis_title='Saldo', 
            xaxis_title='Settimana',
            xaxis=dict(tickmode='linear'),  # Mostra tutti i tick sull'asse X
            yaxis=dict(showticklabels=False),  # Nascondi tutti i tick sull'asse Y
        )
        
        st.plotly_chart(fig)

    with tab2:
        st.dataframe(
            df_settimanale[['SETTIMANA','SALDO_SETT_FORMATTED']], 
            hide_index=True, width=100000, 
            column_config={"SALDO_SETT_FORMATTED": st.column_config.Column(label="SALDO SETTIMANALE (Ore:Minuti)")}
        ) 

with col2:

    st.subheader("Report mensile :bookmark_tabs:")
    st.text("Questa sezione mostra il saldo aggregato per mese")
    tab1, tab2 = st.tabs(["Grafico", "Dati"])
    
    with tab1: 
        # Converti timedelta in ore decimali per la rappresentazione numerica
        df_mensile['SALDO_GIORNALIERO_ORE'] = df_mensile['SALDO GIORNALIERO'].dt.total_seconds() / 3600
        # Applica la funzione al saldo giornaliero per formattare le etichette
        df_mensile['SALDO_GIORNALIERO_FORMATTED'] = df_mensile['SALDO GIORNALIERO'].apply(format_saldo)
        # Crea una lista di colori in base ai valori positivi o negativi
        colors = ['mediumseagreen' if x >= 0 else 'firebrick' for x in df_mensile['SALDO_GIORNALIERO_ORE']]        
        # Crea il grafico manualmente con go.Bar
        fig = go.Figure(data=[
            go.Bar(
                x=df_mensile['MESE'],
                y=df_mensile['SALDO_GIORNALIERO_ORE'],
                text=df_mensile['SALDO_GIORNALIERO_FORMATTED'],
                textposition='outside',
                marker_color=colors  # Applica il colore condizionale
            )
        ])

        # Imposta il titolo del grafico
        fig.update_layout(
            # title_text='Saldo per mese', 
            yaxis_title='Saldo', 
            xaxis_title='Mese',
            xaxis=dict(tickmode='linear'),  # Mostra tutti i tick sull'asse X
            yaxis=dict(showticklabels=False),  # Nascondi tutti i tick sull'asse Y
        )
        
        st.plotly_chart(fig)

    with tab2:
        st.dataframe(df_mensile[['MESE','SALDO_MENSILE_FORMATTED']], 
                     hide_index=True, 
                     width=100000,
                     column_config={"SALDO_MENSILE_FORMATTED": st.column_config.Column(label="SALDO MENSILE (Ore:Minuti)")})
