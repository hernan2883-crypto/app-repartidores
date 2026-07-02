import streamlit as st
import gspread
import json
from google.oauth2.service_account import Credentials

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Reparto Panadería", page_icon="🍞", layout="centered")

# --- CONEXIÓN ---
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
    except Exception as e:
        st.error(f"Error al conectar: {e}")
        st.stop()

# --- FUNCIONES DE LIMPIEZA ---
def convertir_a_float(valor):
    """Limpia strings tipo '$ 1.500,50' y los convierte a numero real"""
    if isinstance(valor, (int, float)): return float(valor)
    if not valor: return 0.0
    s = str(valor).replace("$", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(s)
    except:
        return 0.0

# --- ESTADO Y CARGA ---
if "reparto" not in st.session_state: st.session_state.reparto = None
if "idx_cliente" not in st.session_state: st.session_state.idx_cliente = 0
if "monto_calculadora" not in st.session_state: st.session_state.monto_calculadora = ""

if "data_control" not in st.session_state:
    with st.spinner("Cargando datos..."):
        st.session_state.data_clientes = st.session_state.hoja_clientes.get_all_records()
        st.session_state.data_control = st.session_state.control_hoja.get_all_records()
        
        # Mapeo simple de zonas
        mapping = {str(r.get("Cliente", "")).strip(): str(r.get("Zona / Reparto", "")).strip().upper() 
                   for r in st.session_state.data_clientes if r.get("Cliente")}
        st.session_state.mapping_zonas = mapping

# --- LÓGICA DE INTERFAZ ---
if st.session_state.reparto is None:
    st.title("🍞 Sistema de Reparto")
    zona = st.selectbox("Seleccioná la zona:", ["P", "C"])
    if st.button("Iniciar Reparto"):
        st.session_state.reparto = zona
        # Filtrar clientes por zona
        lista = [r for r in st.session_state.data_control 
                 if st.session_state.mapping_zonas.get(str(r.get("Cliente", "")).strip()) == zona]
        # Ordenar por columna 'salida'
        st.session_state.lista_filtrada = sorted(lista, key=lambda x: int(x.get("salida", 9999)))
        st.rerun()
else:
    lista = st.session_state.lista_filtrada
    idx = st.session_state.idx_cliente
    cliente = lista[idx]
    
    st.subheader(cliente["Cliente"])
    
    # Lectura de deuda (Columna C es el índice 2)
    # Buscamos la columna que contenga "deuda" en el nombre, o usamos la 3ra columna
    col_deuda = next((k for k in cliente.keys() if "deuda" in k.lower()), list(cliente.keys())[2])
    deuda = convertir_a_float(cliente.get(col_deuda, 0))
    
    st.info(f"Deuda Anterior: ${deuda:,.2f}")
    
    # Calculadora
    col1, col2, col3 = st.columns(3)
    # ... (Aquí irían tus botones de calculadora iguales a antes)
    # Asegúrate que al presionar 'Cargar' uses:
    if st.button("CARGAR PAGO"):
        fila = st.session_state.control_hoja.find(cliente["Cliente"]).row
        st.session_state.control_hoja.update_cell(fila, 12, float(st.session_state.monto_calculadora or 0))
        st.success("Guardado")
