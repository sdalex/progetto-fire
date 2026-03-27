import streamlit as st
import pandas as pd
import numpy as np
import datetime
import plotly.graph_objects as go

st.set_page_config(page_title="Simulatore FIRE", layout="wide")
st.title("🔥 Simulatore FIRE: Accumulo & Decumulo")
st.write("Calcola il tuo percorso verso l'indipendenza finanziaria e simula i prelievi durante la pensione anticipata.")

# --- 1. IL "MOTORE" DEL SIMULATORE (Aggiornato con Decumulo) ---
def simula_monte_carlo(p_iniziale, r_mensile_base, spese, rend_nom, infl, tasse, swr, vol, n_sim, anni_totali, bonus_euro, bonus_anno, incremento_r, anno_incremento):
    target = spese / swr
    rend_reale = rend_nom - (rend_nom * tasse) - infl
    mesi_totali = anni_totali * 12
    spesa_mensile = spese / 12  # Quanto preleverai ogni mese in FIRE
    
    tutte_le_traiettorie = {}
    
    for i in range(n_sim):
        patrimonio = p_iniziale
        percorso = []
        in_fire = False # L'interruttore: partiamo che NON siamo in FIRE
        
        for mese in range(mesi_totali):
            rend_random_annuo = np.random.normal(rend_reale, vol)
            rend_random_mensile = (1 + rend_random_annuo) ** (1/12) - 1
            
            # Controllo: abbiamo raggiunto l'indipendenza?
            if patrimonio >= target and not in_fire:
                in_fire = True # Scatta l'interruttore! Smettiamo di lavorare.
            
            if not in_fire:
                # --- FASE DI ACCUMULO ---
                risparmio_attuale = r_mensile_base
                if mese >= (anno_incremento * 12):
                    risparmio_attuale += incremento_r
                patrimonio += risparmio_attuale
            else:
                # --- FASE DI DECUMULO (Pensione Anticipata) ---
                # Non aggiungiamo più il risparmio, ma preleviamo per vivere!
                patrimonio -= spesa_mensile
                
            # Controllo Evento Extra (Bonus/Eredità)
            if mese == (bonus_anno * 12) - 1:
                patrimonio += bonus_euro
                
            # Il mercato agisce su ciò che rimane investito
            patrimonio *= (1 + rend_random_mensile)
            
            # Se i soldi finiscono, restano a zero (non andiamo in debito)
            if patrimonio < 0:
                patrimonio = 0
                
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
spese_annuali = st.sidebar.number_input("Spese annuali in FIRE (€)", value=24000, step=1000)

st.sidebar.header("🚀 Crescita Professionale")
incremento_risparmio = st.sidebar.number_input("Aumento futuro risparmio (€/mese)", value=0, step=50)
anno_incremento = st.sidebar.number_input("Tra quanti anni?", value=3, min_value=1, max_value=anni_restanti)

st.sidebar.header("🎁 Eventi Straordinari")
importo_bonus = st.sidebar.number_input("Importo una tantum (€)", value=0, step=5000)
anno_del_bonus = st.sidebar.number_input("Tra quanti anni (bonus)?", value=10, min_value=1, max_value=anni_restanti)

st.sidebar.header("📈 Mercato & Tasse")
rend_nom = st.sidebar.slider("Rendimento Lordo (%)", 1.0, 12.0, 7.0) / 100
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

# --- 4. CALCOLO DELLA DATA DI LIBERTÀ ---
st.subheader("🗓️ Il tuo responso FIRE")
mediana_patrimonio = df_sim.median(axis=1)

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
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Anno del FIRE", f"{anno_calendario_fire}")
    c2.metric("La tua età al FIRE", f"{eta_al_fire} anni")
    c3.metric("Tempo d'attesa", f"{anni_al_fire} anni e {mesi_extra} mesi")
    
    st.success(f"🎉 Raggiungerai l'indipendenza finanziaria nel **{anno_calendario_fire}**, all'età di **{eta_al_fire} anni**.")
else:
    st.warning("⚠️ Con i parametri attuali, non raggiungerai il target FIRE entro l'aspettativa di vita.")

# --- 5. GRAFICO INTERATTIVO PRO (Plotly) ---
st.subheader(f"📈 Proiezione: Accumulo e Decumulo (Target: € {capitale_target:,.0f})")

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
    line=dict(color='red', width=2, dash='dash'), name='Soglia FIRE'
))

fig.update_layout(
    xaxis_title="Anno", 
    yaxis_title="Patrimonio (€)", 
    hovermode="x unified", 
    template="plotly_white", 
    margin=dict(l=0, r=0, t=30, b=0),
    yaxis=dict(rangemode='tozero') # Forza l'asse Y a partire da zero per vedere i fallimenti
)
st.plotly_chart(fig, use_container_width=True)

# --- 6. ESPORTAZIONE ---
st.divider()
csv = df_sim.to_csv(index=True).encode('utf-8')
st.download_button("📥 Scarica dati in CSV", data=csv, file_name='simulazione_fire.csv', mime='text/csv')
