import streamlit as st
import pandas as pd
import numpy as np
import datetime
import plotly.graph_objects as go

st.set_page_config(page_title="Simulatore FIRE", layout="wide")
st.title("🔥 Simulatore FIRE")
st.write("Calcola il tuo percorso verso l'indipendenza finanziaria con simulazioni avanzate, bonus e scatti di carriera.")

# --- 1. IL "MOTORE" DEL SIMULATORE (Aggiornato con Carriera) ---
def simula_monte_carlo(p_iniziale, r_mensile_base, spese, rend_nom, infl, tasse, swr, vol, n_sim, anni_totali, bonus_euro, bonus_anno, incremento_r, anno_incremento):
    """
    Esegue una simulazione statistica del patrimonio basata su rendimenti casuali.
    
    Args:
        p_iniziale (float): Capitale di partenza.
        r_mensile_base (float): Risparmio mensile attuale.
        ... [e così via per gli altri parametri]
    
    Returns:
        pd.DataFrame: Tabella con tutte le simulazioni.
        float: Capitale target calcolato.
    """
    target = spese / swr
    rend_reale = rend_nom - (rend_nom * tasse) - infl
    mesi_totali = anni_totali * 12
    
    tutte_le_traiettorie = {}
    
    for i in range(n_sim):
        patrimonio = p_iniziale
        percorso = []
        for mese in range(mesi_totali):
            rend_random_annuo = np.random.normal(rend_reale, vol)
            rend_random_mensile = (1 + rend_random_annuo) ** (1/12) - 1
            
            # 1. GESTIONE DEL RISPARMIO MENSILE (Logica della Carriera)
            risparmio_attuale = r_mensile_base
            # Se il mese attuale ha superato la data della promozione...
            if mese >= (anno_incremento * 12):
                risparmio_attuale += incremento_r # ...aggiungi l'aumento!
                
            patrimonio += risparmio_attuale
            
            # 2. CONTROLLO EVENTO EXTRA (Bonus/Eredità)
            if mese == (bonus_anno * 12) - 1:
                patrimonio += bonus_euro
                
            # 3. APPLICAZIONE DEL RENDIMENTO SUL MERCATO
            patrimonio *= (1 + rend_random_mensile)
            percorso.append(patrimonio)
        
        tutte_le_traiettorie[f"Sim {i+1}"] = percorso
        
    return pd.DataFrame(tutte_le_traiettorie), target


# --- 2. INTERFACCIA E INPUT UTENTE ---
st.sidebar.header("⏳ Il tuo Tempo")
eta_attuale = st.sidebar.number_input("La tua età attuale", value=30, min_value=18, max_value=100)
aspettativa_vita = st.sidebar.number_input("Aspettativa di vita (anni)", value=85, min_value=50, max_value=120)

anni_restanti = aspettativa_vita - eta_attuale
anno_corrente = datetime.datetime.now().year
anno_fine = anno_corrente + anni_restanti

st.sidebar.header("👤 Parametri Personali")
p_iniziale = st.sidebar.number_input("Patrimonio attuale (€)", value=10000, step=1000)
r_mensile = st.sidebar.number_input("Risparmio mensile attuale (€)", value=500, step=50)
spese_annuali = st.sidebar.number_input("Spese annuali desiderate (€)", value=24000, step=1000)

# NUOVA SEZIONE: Crescita Professionale
st.sidebar.header("🚀 Crescita Professionale")
incremento_risparmio = st.sidebar.number_input("Aumento futuro del risparmio mensile (€)", value=0, step=50, help="Quanto risparmierai IN PIÙ al mese dopo la promozione?")
anno_incremento = st.sidebar.number_input("Tra quanti anni inizierai a risparmiare di più?", value=3, min_value=1, max_value=anni_restanti)

st.sidebar.header("🎁 Eventi Straordinari")
importo_bonus = st.sidebar.number_input("Importo una tantum (Eredità/TFR) (€)", value=0, step=5000)
anno_del_bonus = st.sidebar.number_input("Tra quanti anni lo riceverai?", value=10, min_value=1, max_value=anni_restanti)

st.sidebar.header("📈 Mercato & Tasse")
rend_nom = st.sidebar.slider("Rendimento Lordo (%)", 1.0, 12.0, 10.0) / 100
volatilita = st.sidebar.slider("Rischio/Volatilità (%)", 5.0, 25.0, 15.0) / 100
inflazione = st.sidebar.slider("Inflazione (%)", 0.0, 5.0, 2.0) / 100
n_simulazioni = st.sidebar.select_slider("Numero Simulazioni", options=[10, 50, 100], value=50)

tasse_cg = 0.26 
swr = 0.04      

# --- 3. ESECUZIONE DEI CALCOLI ---
df_sim, capitale_target = simula_monte_carlo(
    p_iniziale, r_mensile, spese_annuali, rend_nom, inflazione, tasse_cg, swr, 
    volatilita, n_simulazioni, anni_restanti, importo_bonus, anno_del_bonus, 
    incremento_risparmio, anno_incremento
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

# --- 4. CALCOLO DELLA DATA DI LIBERTÀ (FIRE DATE) ---
st.subheader("🗓️ Il tuo responso FIRE")
mediana_patrimonio = df_sim.median(axis=1)

mese_fire = None
for mese, valore in enumerate(mediana_patrimonio):
    if valore >= capitale_target:
        mese_fire = mese + 1
        break

if mese_fire:
    anni_al_fire = mese_fire / 12
    mesi_extra = mese_fire % 12
    eta_al_fire = eta_attuale + anni_al_fire
    anno_calendario_fire = anno_corrente + anni_al_fire
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Anno del FIRE", f"{anno_calendario_fire}")
    c2.metric("La tua età al FIRE", f"{eta_al_fire} anni")
    c3.metric("Tempo d'attesa", f"{anni_al_fire} anni e {mesi_extra} mesi")
    
    st.success(f"🎉 Raggiungerai l'indipendenza finanziaria nel **{anno_calendario_fire}**, all'età di **{eta_al_fire} anni**.")
else:
    st.warning("⚠️ Con i parametri attuali, non raggiungerai il target FIRE entro l'aspettativa di vita.")

# --- 5. GRAFICO INTERATTIVO PRO (Plotly) ---
st.subheader(f"📈 Proiezione della crescita (Target: € {capitale_target:,.0f})")

anni_asse_x = [(mese / 12) + anno_corrente for mese in df_sim.index]
fig = go.Figure()

for col in df_sim.columns[:50]:
    fig.add_trace(go.Scatter(
        x=anni_asse_x, y=df_sim[col], mode='lines',
        line=dict(width=1, color='rgba(100, 149, 237, 0.3)'), showlegend=False, name="Simulazione"
    ))

fig.add_trace(go.Scatter(
    x=anni_asse_x, y=mediana_patrimonio, mode='lines',
    line=dict(width=3, color='royalblue'), name='Percorso Medio'
))

fig.add_trace(go.Scatter(
    x=anni_asse_x, y=[capitale_target] * len(anni_asse_x), mode='lines',
    line=dict(color='red', width=2, dash='dash'), name='OBIETTIVO FIRE'
))

fig.update_layout(xaxis_title="Anno", yaxis_title="Patrimonio (€)", hovermode="x unified", template="plotly_white", margin=dict(l=0, r=0, t=30, b=0))
st.plotly_chart(fig, use_container_width=True)

# --- 6. ESPORTAZIONE ---
st.divider()
csv = df_sim.to_csv(index=True).encode('utf-8')
st.download_button("📥 Scarica dati in CSV", data=csv, file_name='simulazione_fire.csv', mime='text/csv')

# --- 7. SEZIONE FAQ ---
st.divider()
st.header("❓ Domande Frequenti (FAQ)")

with st.expander("Come viene calcolato il Target FIRE?"):
    st.write("""
        Il simulatore utilizza la **Regola del 4%** (SWR - Safe Withdrawal Rate). 
        Il capitale necessario è calcolato come:  
        $$Target = \frac{Spese \ Annuali}{0.04}$$  
        Questa formula indica la somma necessaria per poter prelevare annualmente quanto ti serve senza intaccare il capitale nel lungo termine.
    """)

with st.expander("Cos'è la simulazione Monte Carlo?"):
    st.write("""
        A differenza di un calcolo lineare, la simulazione **Monte Carlo** tiene conto del rischio. 
        Genera molteplici scenari casuali basati sulla **volatilità** (deviazione standard). 
        Il 'Percorso Medio' rappresenta la mediana dei risultati, mentre le zone d'ombra mostrano quanto i mercati possono oscillare.
    """)

with st.expander("I valori sono al lordo o al netto di tasse e inflazione?"):
    st.write("""
        I risultati sono presentati in **valore reale netto**.  
        Il simulatore applica automaticamente:
        1. Una tassazione del **26%** sulle plusvalenze.
        2. Una riduzione basata sull'**inflazione** per mostrarti il potere d'acquisto effettivo futuro.
    """)

with st.expander("Come funzionano i Bonus e gli Aumenti?"):
    st.write("""
        - **Bonus/Eredità:** Viene aggiunto interamente al patrimonio nel mese X dell'anno impostato.
        - **Crescita Professionale:** Aumenta il tuo risparmio mensile in modo permanente a partire dall'anno scelto. Entrambi beneficiano dell'interesse composto da quel momento in poi.
    """)
