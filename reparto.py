import streamlit as st
import gspread
import json
from google.oauth2.service_account import Credentials

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Reparto Panadería", page_icon="🍞", layout="centered")

# --- ESTILOS VISUALES (FORZANDO 3 COLUMNAS SIEMPRE) ---
st.markdown("""
<style>
    /* Forzar que las columnas se mantengan en 33% de ancho en todo momento */
    [data-testid="column"] {
        width: 33.33% !important;
        flex: 1 1 33.33% !important;
        min-width: 33.33% !important;
    }
    /* Estilo de botones */
    .stButton > button {
        height: 55px !important;
        width: 100% !important;
        font-weight: bold;
    }
    /* Caja de resultados */
    .caja-saldos {
        background-color: #F3F4F6;
        padding: 10px;
        border-radius: 12px;
        text-align: center;
        font-size: 1.5rem !important;
        border: 1px solid #E5E7EB;
    }
    .caja-deuda {
        background-color: #FEF2F2;
        padding: 10px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 10px;
        border: 1px solid #FCA5A5;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN (OPTIMIZADA CON CACHÉ) ---
@st.cache_resource
def conectar_sheets():
    informacion = json.loads(st.secrets["gcp_json"])
    alcances = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credenciales = Credentials.from_service_account_info(informacion, scopes=alcances)
    return gspread.authorize(credenciales)

if "hoja_clientes" not in st.session_state:
    try:
        gc = conectar_sheets()
        doc = gc.open("Planilla_Maestra_Panaderia")
        st.session_state.hoja_clientes = doc.worksheet("Clientes")
        st.session_state.control_hoja = doc.worksheet("Control-Diario")
    except Exception as mi:
        st.error(f"Error: {mi}")
        st.stop()

# --- 3. VARIABLES DE SESIÓN ---
if "reparto" not in st.session_state: st.session_state.reparto = None
if "idx_cliente" not in st.session_state: st.session_state.idx_cliente = 0
if "monto_calculadora" not in st.session_state: st.session_state.monto_calculadora = ""
if "lista_filtrada" not in st.session_state: st.session_state.lista_filtrada = []
if "mapping_zonas" not in st.session_state: st.session_state.mapping_zonas = {}

# --- 4. CARGA DE DATOS ---
if "data_control" not in st.session_state:
    with st.spinner("Sincronizando..."):
        try:
            st.session_state.data_clientes = st.session_state.hoja_clientes.get_all_records()
            st.session_state.data_control = st.session_state.control_hoja.get_all_records()
            mapping = {}
            for row in st.session_state.data_clientes:
                keys = list(row.keys())
                key_cliente = next((k for k in keys if 'nombre' in k.lower() or 'razón' in k.lower() or k.lower() == 'cliente'), None)
                key_zona = next((k for k in keys if 'zona' in k.lower() or 'reparto' in k.lower()), None)
                if key_cliente and key_zona:
                    nom = str(row.get(key_cliente, '')).strip()
                    zon = str(row.get(key_zona, '')).strip().upper()
                    if nom: mapping[nom] = zon
            st.session_state.mapping_zonas = mapping
        except Exception as e:
            st.error(f"Error de carga: {e}")
            st.stop()

# --- FUNCIONES ---
def click_numero(digito): st.session_state.monto_calculadora += str(digito)
def click_borrar(): st.session_state.monto_calculadora = st.session_state.monto_calculadora[:-1]
def click_limpiar(): st.session_state.monto_calculadora = ""
def avanzar_cliente():
    if st.session_state.idx_cliente < len(st.session_state.lista_filtrada) - 1:
        st.session_state.idx_cliente += 1
        st.session_state.monto_calculadora = ""
def retroceder_cliente():
    if st.session_state.idx_cliente > 0:
        st.session_state.idx_cliente -= 1
        st.session_state.monto_calculadora = ""

# --- INTERFAZ ---
if st.session_state.reparto is None:
    st.title("🍞 Sistema de Reparto")
    reparto_elegido = st.selectbox("Salida / Reparto:", ["P", "C"])
    if st.button("Iniciar Reparto", type="primary", use_container_width=True):
        st.session_state.reparto = reparto_elegido
        clientes_filtrados = [row for row in st.session_state.data_control if st.session_state.mapping_zonas.get(str(row.get('Cliente', '')).strip()) == reparto_elegido]
        st.session_state.lista_filtrada = sorted(clientes_filtrados, key=lambda x: int(x.get('salida', 9999)) if str(x.get('salida', '')).isdigit() else 9999)
        st.session_state.idx_cliente = 0
        st.rerun()
else:
    lista = st.session_state.lista_filtrada
    idx = max(0, min(st.session_state.idx_cliente, len(lista) - 1))
    st.session_state.idx_cliente = idx
    cliente_actual = lista[idx]
    
    if st.button("⬅️ Cambiar Zona"):
        st.session_state.reparto = None
        st.rerun()
        
    st.markdown(f"<h1 style='text-align: center;'>{cliente_actual['Cliente']}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center;'>Orden: #{cliente_actual.get('salida', '-')}</p>", unsafe_allow_html=True)
    
    # Calculadora
    monto_texto = st.session_state.monto_calculadora if st.session_state.monto_calculadora != "" else "0"
    st.markdown(f"<div class='caja-saldos'>Paga hoy: ${float(monto_texto):,.2f}</div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.button("1", on_click=click_numero, args=("1",))
        st.button("4", on_click=click_numero, args=("4",))
        st.button("7", on_click=click_numero, args=("7",))
        st.button("⌫", on_click=click_borrar)
    with col2:
        st.button("2", on_click=click_numero, args=("2",))
        st.button("5", on_click=click_numero, args=("5",))
        st.button("8", on_click=click_numero, args=("8",))
        st.button("0", on_click=click_numero, args=("0",))
    with col3:
        st.button("3", on_click=click_numero, args=("3",))
        st.button("6", on_click=click_numero, args=("6",))
        st.button("9", on_click=click_numero, args=("9",))
        st.button("C", on_click=click_limpiar)
        
    st.button("🚚 CARGAR PAGO", type="primary", use_container_width=True, on_click=lambda: None) # Aquí pondrías tu lógica de carga
