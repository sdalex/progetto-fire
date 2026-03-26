import streamlit as st
import pandas as pd
import numpy as np
import datetime # NUOVA LIBRERIA: Serve per gestire date e anni!

# Configurazione iniziale della pagina
st.set_page_config(page_title="Simulatore FIRE", layout="wide")
st.title("🔥 Simulatore FIRE")
st.write("Calcola il tuo percorso verso l'indipendenza finanziaria basato sulla tua aspettativa di vita.")

# --- 1. IL "MOTORE" DEL SIMULATORE ---
def simula_monte_carlo(p_iniziale, risparmio, spese, rend_nom, infl, tasse, swr, vol, n_sim, anni_totali):
    target = spese / swr
    rend_reale = rend_nom - (rend_nom * tasse) - infl

    # NOVITÀ: I mesi totali ora dipendono dai tuoi anni restanti!
    mesi_totali = anni_totali * 12

    tutte_le_traiettorie = {}

    for i in range(n_sim):
        patrimonio = p_iniziale
        percorso = []
        for mese in range(mesi_totali):
            rend_random_annuo = np.random.normal(rend_reale, vol)
            rend_random_mensile = (1 + rend_random_annuo) ** (1/12) - 1

            patrimonio += risparmio
            patrimonio *= (1 + rend_random_mensile)
            percorso.append(patrimonio)

        tutte_le_traiettorie[f"Sim {i+1}"] = percorso

    return pd.DataFrame(tutte_le_traiettorie), target


# --- 2. INTERFACCIA E INPUT UTENTE ---

# NOVITÀ: Sezione per il Tempo di Vita
st.sidebar.header("⏳ Il tuo Tempo")
eta_attuale = st.sidebar.number_input("La tua età attuale", value=30, min_value=18, max_value=100)
aspettativa_vita = st.sidebar.number_input("Aspettativa di vita (anni)", value=85, min_value=50, max_value=120)

# Calcoli automatici del tempo
anni_restanti = aspettativa_vita - eta_attuale
anno_corrente = datetime.datetime.now().year # Chiede al computer l'anno attuale
anno_fine = anno_corrente + anni_restanti

# Mostriamo un piccolo riquadro informativo con i calcoli automatici
st.sidebar.success(f"**Anni restanti:** {anni_restanti}\n\n**Anno di riferimento finale:** {anno_fine}")

st.sidebar.divider()

st.sidebar.header("Parametri Personali")
p_iniziale = st.sidebar.number_input("Patrimonio attuale (€)", value=10000, step=1000)
r_mensile = st.sidebar.number_input("Risparmio mensile (€)", value=500, step=50)
spese_annuali = st.sidebar.number_input("Spese annuali desiderate (€)", value=24000, step=1000)

st.sidebar.header("Mercato & Tasse")
rend_nom = st.sidebar.slider("Rendimento Lordo (%)", 1.0, 12.0, 7.0) / 100
volatilita = st.sidebar.slider("Rischio/Volatilità (%)", 5.0, 25.0, 15.0) / 100
inflazione = st.sidebar.slider("Inflazione (%)", 0.0, 5.0, 2.0) / 100
n_simulazioni = st.sidebar.select_slider("Numero Simulazioni", options=[10, 50, 100], value=50)

tasse_cg = 0.26
swr = 0.04


# --- 3. ESECUZIONE DEI CALCOLI ---
# Passiamo 'anni_restanti' alla funzione al posto del numero fisso
df_sim, capitale_target = simula_monte_carlo(
    p_iniziale, r_mensile, spese_annuali, rend_nom, inflazione, tasse_cg, swr, volatilita, n_simulazioni, anni_restanti
)


# --- 4. TABELLA DI SINTESI DINAMICA ---
st.subheader("📋 Traguardi nel tempo")

# NOVITÀ: La tabella ora si adatta in base a quanti anni ti mancano!
# Controlliamo a 10 anni, a metà del percorso, e alla fine (aspettativa di vita)
meta_percorso = int(anni_restanti / 2)
anni_da_controllare = [10, meta_percorso, anni_restanti]

# Rimuoviamo eventuali duplicati (es. se ti mancano 10 anni in totale) e mettiamo in ordine
anni_da_controllare = sorted(list(set([a for a in anni_da_controllare if a <= anni_restanti and a > 0])))

riassunto = []

for anno_target in anni_da_controllare:
    mese_indice = (anno_target * 12) - 1
    valori_mese = df_sim.iloc[mese_indice]

    caso_peggiore = np.percentile(valori_mese, 10)
    caso_medio = np.median(valori_mese)
    caso_migliore = np.percentile(valori_mese, 90)

    # Calcoliamo anche l'anno di calendario corrispondente
    anno_calendario = anno_corrente + anno_target

    etichetta = f"Tra {anno_target} Anni ({anno_calendario})"
    if anno_target == anni_restanti:
         etichetta = f"Fine Vita a {aspettativa_vita} anni ({anno_calendario})"

    riassunto.append({
        "Scadenza": etichetta,
        "Caso Peggiore (Pessimista)": f"€ {caso_peggiore:,.0f}",
        "Caso Medio (Realista)": f"€ {caso_medio:,.0f}",
        "Caso Migliore (Ottimista)": f"€ {caso_migliore:,.0f}"
    })

st.table(pd.DataFrame(riassunto).set_index("Scadenza"))


# --- 5. GRAFICO E TARGET ---
# st.subheader(f"📈 Crescita del Patrimonio (Target FIRE: € {capitale_target:,.0f})")
# st.write(f"Questa proiezione simula il tuo patrimonio fino all'anno {anno_fine}.")
# Modifichiamo l'asse X del grafico per mostrare gli anni invece dei mesi
# df_sim.index = [(mese / 12) + anno_corrente for mese in df_sim.index]
# st.line_chart(df_sim)

# --- 5. CALCOLO DELLA DATA DI LIBERTÀ (FIRE DATE) ---
st.divider()
st.subheader("🗓️ Il tuo responso FIRE")

# Calcoliamo la mediana di tutti i percorsi mese per mese
mediana_patrimonio = df_sim.median(axis=1)

# Cerchiamo il primo mese in cui la mediana supera il capitale target
mese_fire = None
for mese, valore in enumerate(mediana_patrimonio):
    if valore >= capitale_target:
        mese_fire = mese + 1
        break

if mese_fire:
    anni_al_fire = mese_fire // 12
    mesi_extra = mese_fire % 12
    eta_al_fire = eta_attuale + anni_al_fire
    anno_calendario_fire = anno_corrente + anni_al_fire

    # Creiamo tre colonne per un look professionale
    c1, c2, c3 = st.columns(3)
    c1.metric("Anno del FIRE", f"{anno_calendario_fire}")
    c2.metric("La tua età al FIRE", f"{eta_al_fire} anni")
    c3.metric("Tempo d'attesa", f"{anni_al_fire} anni e {mesi_extra} mesi")

    st.success(f"🎉 Grandi notizie! Raggiungerai l'indipendenza finanziaria nel **{anno_calendario_fire}**, all'età di **{eta_al_fire} anni**.")
    st.balloons() # Festeggiamo!
else:
    st.warning("⚠️ Con i parametri attuali (risparmio/rendimento), non raggiungerai il target FIRE entro la tua aspettativa di vita. Prova ad aumentare il risparmio mensile o a ridurre le spese previste.")

# --- 6. GRAFICO E TARGET ---
st.subheader(f"📈 Proiezione della crescita (Target: € {capitale_target:,.0f})")
# (Il resto del codice del grafico rimane uguale...)
df_sim_grafico = df_sim.copy()
df_sim_grafico.index = [(mese / 12) + anno_corrente for mese in df_sim_grafico.index]
st.line_chart(df_sim_grafico)


# --- 6. ESPORTAZIONE PER GOOGLE SHEETS ---
st.divider()
csv = df_sim.to_csv(index=True).encode('utf-8')
st.download_button("📥 Scarica dati in CSV", data=csv, file_name='simulazione_fire.csv', mime='text/csv')
