import streamlit as st
import gspread
import json
from google.oauth2.service_account import Credentials

# --- FUNCIÓN DE LIMPIEZA DE DINERO ---
def limpiar_dinero(valor):
    if not valor: return 0.0
    # Limpiamos signos de pesos, puntos y comas para que sea un número real
    s = str(valor).replace("$", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(s)
    except:
        return 0.0

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Reparto Panadería", page_icon="🍞", layout="centered")

# Estilos visuales para la interfaz
st.markdown("""
<style>
.caja-saldos { background-color: #F3F4F6; padding: 15px; border-radius: 12px; text-align: center; font-size: 20px !important; margin-bottom: 15px; border: 1px solid #E5E7EB; }
.caja-deuda { background-color: #FEF2F2; padding: 12px; border-radius: 12px; text-align: center; font-size: 18px !important; margin-bottom: 15px; border: 1px solid #FCA5A5; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN AUTENTICADA ---
@st.cache_resource
def conectar_sheets():
    informacion = json.loads(st.secrets["gcp_json"])
    alcances = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credenciales = Credentials.from_service_account_info(informacion, scopes=alcances)
    return gspread.authorize(credenciales)

if "hoja_clientes" not in st.session_state or "control_hoja" not in st.session_state:
    try:
        gc = conectar_sheets()
        doc = gc.open("Planilla_Maestra_Panaderia")
        st.session_state.hoja_clientes = doc.worksheet("Clientes")
        st.session_state.control_hoja = doc.worksheet("Control-Diario")
    except Exception as mi:
        st.error(f"Error al conectar: {mi}")
        st.stop()

# --- 3. VARIABLES EN MEMORIA ---
if "reparto" not in st.session_state: st.session_state.reparto = None
if "idx_cliente" not in st.session_state: st.session_state.idx_cliente = 0
if "monto_calculadora" not in st.session_state: st.session_state.monto_calculadora = ""
if "lista_filtrada" not in st.session_state: st.session_state.lista_filtrada = []
if "mapping_zonas" not in st.session_state: st.session_state.mapping_zonas = {}

# --- 4. CARGA DE DATOS ---
if "data_clientes" not in st.session_state or "data_control" not in st.session_state or not st.session_state.mapping_zonas:
    with st.spinner("Sincronizando..."):
        try:
            st.session_state.data_clientes = st.session_state.hoja_clientes.get_all_records()
            st.session_state.data_control = st.session_state.control_hoja.get_all_records()
            mapping = {str(r.get("Cliente", "")).strip(): str(r.get("Zona / Reparto", "")).strip().upper() 
                       for r in st.session_state.data_clientes if r.get("Cliente")}
            st.session_state.mapping_zonas = mapping
        except Exception as e:
            st.error(f"Error al leer: {e}")
            st.stop()

# --- 5. FUNCIONES DE LA CALCULADORA ---
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

# --- PANTALLA 1 ---
if st.session_state.reparto is None:
    st.title("🍞 Sistema de Reparto")
    reparto_elegido = st.selectbox("Salida / Reparto:", ["P", "C"])
    if st.button("Iniciar Reparto"):
        st.session_state.reparto = reparto_elegido
        lista = [r for r in st.session_state.data_control if st.session_state.mapping_zonas.get(str(r.get("Cliente", "")).strip()) == reparto_elegido]
        st.session_state.lista_filtrada = sorted(lista, key=lambda x: int(x.get("salida", 9999)))
        st.session_state.idx_cliente = 0
        st.rerun()
else:
    lista = st.session_state.lista_filtrada
    if not lista:
        st.warning("No hay clientes.")
        if st.button("Volver"): st.session_state.reparto = None; st.rerun()
        st.stop()
        
    idx = st.session_state.idx_cliente
    cliente = lista[idx]
    
    # --- LECTURA COLUMNA C ---
    # Usamos la llave exacta "Deuda Anterior" que aparece en tu imagen
    deuda_raw = cliente.get("Deuda Anterior", "0")
    deuda_float = limpiar_dinero(deuda_raw)
    
    if st.button(f"⬅️ Cambiar Zona"):
        st.session_state.reparto = None; st.rerun()
        
    st.markdown(f"<h1 style='text-align: center; color: #1E3A8A;'>{cliente['Cliente']}</h1>", unsafe_allow_html=True)
    st.markdown(f"<div class='caja-deuda'>⚠️ Deuda Anterior: ${deuda_float:,.2f}</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1: st.button("◀️ Anterior", on_click=retroceder_cliente, use_container_width=True)
    with col2: st.button("Siguiente ▶️", on_click=avanzar_cliente, use_container_width=True)
    
    monto_float = float(st.session_state.monto_calculadora or 0)
    st.markdown(f"<div class='caja-saldos'>Paga hoy: ${monto_float:,.2f}</div>", unsafe_allow_html=True)
    
    # Teclado
    c1, c2, c3 = st.columns(3)
    with c1:
        st.button("1", on_click=click_numero, args=("1",), use_container_width=True)
        st.button("4", on_click=click_numero, args=("4",), use_container_width=True)
        st.button("7", on_click=click_numero, args=("7",), use_container_width=True)
        st.button("⌫", on_click=click_borrar, use_container_width=True)
    with c2:
        st.button("2", on_click=click_numero, args=("2",), use_container_width=True)
        st.button("5", on_click=click_numero, args=("5",), use_container_width=True)
        st.button("8", on_click=click_numero, args=("8",), use_container_width=True)
        st.button("0", on_click=click_numero, args=("0",), use_container_width=True)
    with c3:
        st.button("3", on_click=click_numero, args=("3",), use_container_width=True)
        st.button("6", on_click=click_numero, args=("6",), use_container_width=True)
        st.button("9", on_click=click_numero, args=("9",), use_container_width=True)
        st.button("C", on_click=click_limpiar, use_container_width=True)

    if st.button("🚚 CARGAR PAGO Y CONTINUAR", type="primary", use_container_width=True):
        fila = st.session_state.control_hoja.find(cliente["Cliente"]).row
        st.session_state.control_hoja.update_cell(fila, 12, float(st.session_state.monto_calculadora or 0))
        st.success("Guardado")
        avanzar_cliente()
        st.rerun()
