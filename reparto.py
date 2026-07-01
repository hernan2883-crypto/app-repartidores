import streamlit as st
import json
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# 1. CONFIGURACIÓN DE PÁGINA PARA CELULAR
st.set_page_config(page_title="Reparto Panadería", layout="centered")

# CSS para botones GIGANTES (fácil de usar arriba de la camioneta)
st.markdown("""
<style>
    div.stButton > button {
        width: 100% !important;
        height: 65px !important;
        font-size: 22px !important;
        font-weight: bold !important;
        border-radius: 12px !important;
    }
    .titulo-cliente {
        font-size: 32px !important;
        font-weight: bold !important;
        text-align: center;
        color: #1E3A8A;
        margin-bottom: 20px;
    }
    .caja-saldos {
        background-color: #F3F4F6;
        padding: 15px;
        border-radius: 12px;
        text-align: center;
        font-size: 18px !important;
        margin-bottom: 15px;
        border: 1px solid #E5E7EB;
    }
</style>
""", unsafe_allow_html=True)

# 2. CONEXIÓN AUTENTICADA (Usa tu secreto gcp_json que ya funciona)
@st.cache_resource
def conectar_sheets():
    info = json.loads(st.secrets["gcp_json"])
    credenciales = Credentials.from_service_account_info(
        info, 
        scopes=["https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"]
    )
    return gspread.authorize(credenciales)

try:
    gc = conectar_sheets()
    doc = gc.open("Planilla_Maestra_Panaderia")
    hoja_clientes = doc.worksheet("Clientes")
    hoja_control = doc.worksheet("Control-Diario") # Nombre exacto con mayúsculas y guión
except Exception as e:
    st.error(f"Error al conectar con Google Sheets: {e}")
    st.stop()

# 3. VARIABLES EN MEMORIA (SESSION STATE)
if "reparto" not in st.session_state:
    st.session_state.reparto = None
if "idx_cliente" not in st.session_state:
    st.session_state.idx_cliente = 0
if "monto_calculadora" not in st.session_state:
    st.session_state.monto_calculadora = ""

# Funciones de la calculadora en pantalla
def presionar_numero(num):
    st.session_state.monto_calculadora += str(num)

def borrar_numero():
    st.session_state.monto_calculadora = st.session_state.monto_calculadora[:-1]

def limpiar_calculadora():
    st.session_state.monto_calculadora = ""

# --- PANTALLA 1: SELECCIÓN DE REPARTO ---
if st.session_state.reparto is None:
    st.markdown("<h2 style='text-align: center;'>¿Qué reparto vas a hacer hoy?</h2>", unsafe_allow_html=True)
    st.write("")
    
    col_c, col_p = st.columns(2)
    with col_c:
        if st.button("🔴 REPARTO C\n(Chelo)"):
            st.session_state.reparto = "C"
            st.session_state.idx_cliente = 0
            st.rerun()
            
    with col_p:
        if st.button("🔵 REPARTO P\n(Papá)"):
            st.session_state.reparto = "P"
            st.session_state.idx_cliente = 0
            st.rerun()

# --- PANTALLA 2: NAVEGACIÓN Y COBRANZA ---
else:
    datos_clientes = pd.DataFrame(hoja_clientes.get_all_records())
    clientes_filtrados = datos_clientes[datos_clientes['Zona / Reparto'] == st.session_state.reparto].reset_index(drop=True)
    
    if clientes_filtrados.empty:
        st.warning(f"No se encontraron clientes para el Reparto {st.session_state.reparto}")
        if st.button("Volver al Inicio"):
            st.session_state.reparto = None
            st.rerun()
        st.stop()
        
    total_clientes = len(clientes_filtrados)
    idx = st.session_state.idx_cliente
    cliente_actual = clientes_filtrados.iloc[idx]
    
    if st.button(f"⬅️ Cambiar Reparto (Saliendo de {st.session_state.reparto})"):
        st.session_state.reparto = None
        st.rerun()
        
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown(f"<div class='titulo-cliente'>{cliente_actual['Nombre / Razón Social']}</div>", unsafe_allow_html=True)
    
    col_ant, col_sig = st.columns(2)
    with col_ant:
        if st.button("◀️ Anterior"):
            if idx > 0:
                st.session_state.idx_cliente -= 1
                st.session_state.monto_calculadora = ""
                st.rerun()
    with col_sig:
        if st.button("Siguiente ▶️"):
            if idx < total_clientes - 1:
                st.session_state.idx_cliente += 1
                st.session_state.monto_calculadora = ""
                st.rerun()
                
    st.markdown(f"<p style='text-align: center; color: gray;'>Cliente {idx + 1} de {total_clientes}</p>", unsafe_allow_html=True)
    
    monto_pago = float(st.session_state.monto_calculadora) if st.session_state.monto_calculadora else 0.0
    
    st.markdown(f"""
    <div class='caja-saldos'>
        <span style='color: green;'><b>Paga hoy:</b> ${monto_pago:,.2f}</span>
    </div>
    """, unsafe_allow_html=True)
    
    # CALCULADORA DIGITAL EN PANTALLA
    c1, c2, c3 = st.columns(3)
    with c1: st.button("1", on_click=presionar_numero, args=(1,))
    with c2: st.button("2", on_click=presionar_numero, args=(2,))
    with c3: st.button("3", on_click=presionar_numero, args=(3,))
    
    c4, c5, c6 = st.columns(3)
    with c4: st.button("4", on_click=presionar_numero, args=(4,))
    with c5: st.button("5", on_click=presionar_numero, args=(5,))
    with c6: st.button("6", on_click=presionar_numero, args=(6,))
    
    c7, c8, c9 = st.columns(3)
    with c7: st.button("7", on_click=presionar_numero, args=(7,))
    with c8: st.button("8", on_click=presionar_numero, args=(8,))
    with c9: st.button("9", on_click=presionar_numero, args=(9,))
    
    c_borrar, c0, c_limpiar = st.columns(3)
    with c_borrar: st.button("⌫ Borrar", on_click=borrar_numero)
    with c0: st.button("0", on_click=presionar_numero, args=(0,))
    with c_limpiar: st.button("C Limpiar", on_click=limpiar_calculadora)
    
    st.write("")
    
    # GUARDAR DIRECTO EN TU COLUMNA M DE CONTROL-DIARIO
    if st.button("💾 CARGAR PAGO Y CONTINUAR", type="primary"):
        if monto_pago > 0:
            with st.spinner("Guardando pago en Google Sheets..."):
                try:
                    # Buscamos en qué fila de la columna L (columna 12) está el cliente
                    nombres_columna_l = hoja_control.col_values(12)
                    nombre_buscar = str(cliente_actual['Nombre / Razón Social']).strip()
                    
                    nombres_limpios = [str(n).strip() for n in nombres_columna_l]
                    
                    if nombre_buscar in nombres_limpios:
                        fila_destino = nombres_limpios.index(nombre_buscar) + 1
                        
                        # Inyectamos el número en la columna M (columna 13, justo al lado)
                        hoja_control.update_cell(fila_destino, 13, monto_pago)
                        st.success(f"¡Pago de ${monto_pago} guardado para {nombre_buscar}!")
                        
                        # Pasa automáticamente al siguiente cliente de la hoja de ruta
                        if idx < total_clientes - 1:
                            st.session_state.idx_cliente += 1
                            st.session_state.monto_calculadora = ""
                            st.rerun()
                    else:
                        st.error(f"No se encontró a '{nombre_buscar}' en la columna L de Control-Diario.")
                except Exception as e:
                    st.error(f"Error al guardar: {e}")
        else:
            st.warning("Ingrese un monto mayor a 0 antes de continuar.")
