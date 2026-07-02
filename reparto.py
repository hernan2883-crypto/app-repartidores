import streamlit as st
import gspread
import json
from google.oauth2.service_account import Credentials

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Reparto Panadería", page_icon="🍞", layout="centered")

# Estilos visuales para la interfaz
st.markdown("""
<style>
.caja-saldos {
    background-color: #F3F4F6;
    padding: 15px;
    border-radius: 12px;
    text-align: center;
    font-size: 20px !important;
    margin-bottom: 15px;
    border: 1px solid #E5E7EB;
}
.caja-deuda {
    background-color: #FEF2F2;
    padding: 12px;
    border-radius: 12px;
    text-align: center;
    font-size: 18px !important;
    margin-bottom: 15px;
    border: 1px solid #FCA5A5;
}
</style>
""", unsafe_allow_html=True)

# --- 1. FUNCIÓN PARA LIMPIAR FORMATOS DE NÚMEROS EN PESOS ---
def limpiar_monto_pesos(val):
    if not val:
        return 0.0
    # Quitamos espacios y signos de pesos
    s = str(val).strip().replace("$", "").replace(" ", "")
    if not s:
        return 0.0
    
    # Manejo de formato argentino (ej: 1.250,50 o 1250,50)
    if "." in s and "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
        
    try:
        return round(float(s), 2)
    except ValueError:
        return 0.0

# --- 2. CONEXIÓN AUTENTICADA EN SEGUNDO PLANO ---
@st.cache_resource
def conectar_sheets():
    informacion = json.loads(st.secrets["gcp_json"])
    alcances = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credenciales = Credentials.from_service_account_info(informacion, scopes=alcances)
    return gspread.authorize(credenciales)

# Guardamos las hojas en memoria para que no ralenticen la calculadora
if "hoja_clientes" not in st.session_state or "control_hoja" not in st.session_state:
    try:
        gc = conectar_sheets()
        doc = gc.open("Planilla_Maestra_Panaderia")
        st.session_state.hoja_clientes = doc.worksheet("Clientes")
        st.session_state.control_hoja = doc.worksheet("Control-Diario")
    except Exception as mi:
        st.error(f"Error al conectar con Google Sheets: {mi}")
        st.stop()

# --- 3. VARIABLES EN MEMORIA (ESTADO DE LA SESIÓN) ---
if "reparto" not in st.session_state:
    st.session_state.reparto = None
if "idx_cliente" not in st.session_state:
    st.session_state.idx_cliente = 0
if "monto_calculadora" not in st.session_state:
    st.session_state.monto_calculadora = ""
if "lista_filtrada" not in st.session_state:
    st.session_state.lista_filtrada = []
if "mapping_zonas" not in st.session_state:
    st.session_state.mapping_zonas = {}

# --- 4. CARGA Y PROCESAMIENTO OPTIMIZADO (SÓLO UNA VEZ) ---
if "data_clientes" not in st.session_state or "data_control" not in st.session_state or not st.session_state.mapping_zonas:
    with st.spinner("Sincronizando planillas con el servidor..."):
        try:
            st.session_state.data_clientes = st.session_state.hoja_clientes.get_all_records()
            # Traemos todo como matriz pura (lista de listas) para asegurar las posiciones de las columnas
            st.session_state.data_control = st.session_state.control_hoja.get_all_values()
            
            # Mapeo rápido de zonas desde la hoja Clientes
            mapping = {}
            for row in st.session_state.data_clientes:
                keys = list(row.keys())
                key_cliente = next((k for k in keys if 'nombre' in k.lower() or 'razón' in k.lower() or 'razon' in k.lower() or k.lower() == 'cliente'), None)
                key_zona = next((k for k in keys if 'zona' in k.lower() or 'reparto' in k.lower()), None)
                
                if key_cliente and key_zona:
                    nom = str(row.get(key_cliente, '')).strip()
                    zon = str(row.get(key_zona, '')).strip().upper()
                    if nom:
                        mapping[nom] = zon
            st.session_state.mapping_zonas = mapping
        except Exception as e:
            st.error(f"Error al leer los datos de la planilla: {e}")
            st.stop()

# --- 5. FUNCIONES DE LA CALCULADORA (EJECUCIÓN INSTANTÁNEA) ---
def click_numero(digito):
    st.session_state.monto_calculadora += str(digito)

def click_borrar():
    st.session_state.monto_calculadora = st.session_state.monto_calculadora[:-1]

def click_limpiar():
    st.session_state.monto_calculadora = ""

def avanzar_cliente():
    if st.session_state.idx_cliente < len(st.session_state.lista_filtrada) - 1:
        st.session_state.idx_cliente += 1
        st.session_state.monto_calculadora = ""

def retroceder_cliente():
    if st.session_state.idx_cliente > 0:
        st.session_state.idx_cliente -= 1
        st.session_state.monto_calculadora = ""

# --- PANTALLA 1: SELECCIÓN DE REPARTO ---
if st.session_state.reparto is None:
    st.title("🍞 Sistema de Reparto")
    st.subheader("Seleccioná la zona de salida")
    
    reparto_elegido = st.selectbox("Salida / Reparto:", ["P", "C"])
    
    if st.button("Iniciar Reparto", type="primary", use_container_width=True):
        st.session_state.reparto = reparto_elegido
        
        clientes_filtrados = []
        # data_control[0] son las cabeceras, iteramos desde el índice 1 (filas de datos)
        for row in st.session_state.data_control[1:]:
            if len(row) > 1:
                nom_cliente = str(row[1]).strip() # Columna B (Índice 1) es el Cliente
                if st.session_state.mapping_zonas.get(nom_cliente) == reparto_elegido:
                    clientes_filtrados.append(row)
        
        # Ordenamos estrictamente por el número de salida (Columna N = Índice 13)
        def obtener_orden_salida(row):
            if len(row) > 13:
                val = str(row[13]).strip()
            else:
                val = ""
            try:
                return int(val)
            except ValueError:
                return 9999
        
        st.session_state.lista_filtrada = sorted(clientes_filtrados, key=obtener_orden_salida)
        st.session_state.idx_cliente = 0
        st.session_state.monto_calculadora = ""
        st.rerun()

# --- PANTALLA 2: CONTROL DE REPARTO CLIENTE POR CLIENT
