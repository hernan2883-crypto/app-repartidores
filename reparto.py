import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# ---------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA Y ESTILOS
# ---------------------------------------------------------
st.set_page_config(
    page_title="Reparto Panadería",
    page_icon="🚚",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Estilo visual adaptado para uso ágil en la calle (botones grandes)
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        height: 3em;
        font-size: 18px !important;
        font-weight: bold;
        border-radius: 10px;
    }
    .status-card {
        padding: 15px;
        background-color: #f0f2f6;
        border-radius: 10px;
        margin-bottom: 15px;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# CONEXIÓN A GOOGLE SHEETS
# ---------------------------------------------------------
@st.cache_resource
def conectar_google_sheets():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    # Usa las credenciales guardadas en st.secrets
    credenciales_json = dict(st.secrets["gcp_json_puro"])
    credentials = Credentials.from_service_account_info(credenciales_json, scopes=scopes)
    client = gspread.authorize(credentials)
    return client

try:
    gc = conectar_google_sheets()
    # Cambiá "Control_Reparto" por el nombre exacto de tu libro en Google Sheets
    sheet = gc.open("Control_Reparto").sheet1
except Exception as e:
    st.error(f"Error de conexión con Google Sheets: {e}")
    st.stop()

# ---------------------------------------------------------
# GESTIÓN DE PERSISTENCIA EN URL (st.query_params)
# ---------------------------------------------------------
query_params = st.query_params

# Si la URL ya trae el chofer y el índice de cliente, los restauramos
if "chofer" in query_params:
    st.session_state["chofer"] = query_params["chofer"]
if "cliente_idx" in query_params:
    st.session_state["cliente_idx"] = int(query_params["cliente_idx"])
else:
    if "cliente_idx" not in st.session_state:
        st.session_state["cliente_idx"] = 0

# ---------------------------------------------------------
# PANTALLA 1: LOGIN POR CÓDIGO (Sólo si no hay chofer activo)
# ---------------------------------------------------------
if "chofer" not in st.session_state or not st.session_state["chofer"]:
    st.title("🚚 Acceso Repartidores")
    st.write("Ingresá tu código de repartidor para comenzar:")

    codigo_input = st.text_input("Código de Repartidor:", type="password")
    
    if st.button("Ingresar y Comenzar"):
        if codigo_input.strip() != "":
            # Guardamos en sesión y en la URL
            st.session_state["chofer"] = codigo_input.strip()
            st.session_state["cliente_idx"] = 0
            
            st.query_params["chofer"] = codigo_input.strip()
            st.query_params["cliente_idx"] = 0
            st.rerun()
        else:
            st.warning("Por favor ingresá un código válido.")
    st.stop()

# ---------------------------------------------------------
# PANTALLA 2: HOJA DE REPARTO EN CALLE
# ---------------------------------------------------------
chofer_actual = st.session_state["chofer"]

# Cargar datos de entregas desde la planilla
@st.cache_data(ttl=10)
def cargar_datos():
    datos = sheet.get_all_records()
    return pd.DataFrame(datos)

df = cargar_datos()

# Filtrar hoja de reparto por el chofer ingresado (si la planilla tiene columna 'Chofer')
if "Chofer" in df.columns:
    df_chofer = df[df["Chofer"].astype(str) == str(chofer_actual)].reset_index(drop=True)
else:
    df_chofer = df.reset_index(drop=True)

st.sidebar.markdown(f"**Chofer Activo:** {chofer_actual}")

# Botón para cerrar sesión explícitamente
if st.sidebar.button("🚪 Salir de la App"):
    st.query_params.clear()
    st.session_state.clear()
    st.rerun()

if df_chofer.empty:
    st.info("No tenés entregas pendientes asignadas para hoy.")
    if st.button("Cerrar Sesión"):
        st.query_params.clear()
        st.session_state.clear()
        st.rerun()
    st.stop()

# Validar límites del índice de cliente
idx_actual = st.session_state.get("cliente_idx", 0)
if idx_actual >= len(df_chofer):
    idx_actual = len(df_chofer) - 1
if idx_actual < 0:
    idx_actual = 0

cliente_actual = df_chofer.iloc[idx_actual]

# ---------------------------------------------------------
# INTERFAZ PRINCIPAL DEL CLIENTE
# ---------------------------------------------------------
st.caption(f"Cliente {idx_actual + 1} de {len(df_chofer)}")
st.markdown(f"## 🏪 {cliente_actual.get('Cliente', 'Cliente Sin Nombre')}")
st.write(f"📍 **Dirección:** {cliente_actual.get('Direccion', 'No especificada')}")
st.write(f"📦 **Pedido:** {cliente_actual.get('Pedido', 'Sin detalle')}")

estado_previo = cliente_actual.get("Estado", "Pendiente")
st.info(f"Estado actual en planilla: **{estado_previo}**")

# Selección de acción/estado para la entrega
nuevo_estado = st.radio(
    "Confirmar Estado de la Entrega:",
    ["Entregado Ok", "Entregado con Modificación", "No Entregado / Ausente"],
    index=0
)

observacion = st.text_input("Observación / Cambio de pedido:", value="")

# BOTÓN DE GUARDADO E INSTANTÁNEO
if st.button("✅ Confirmar y Guardar Entrega"):
    try:
        # Buscamos la fila exacta en la planilla original para actualizar
        fila_original = df[df['Cliente'] == cliente_actual['Cliente']].index[0] + 2
        
        # Columna de Estado y Observación (Ajustar según los nombres de tus columnas)
        # Ejemplo: Columna E para Estado, Columna F para Observaciones
        sheet.update_cell(fila_original, 4, nuevo_estado)  # Ajustar número de columna
        if observacion:
            sheet.update_cell(fila_original, 5, observacion)
            
        st.success("¡Entrega guardada exitosamente!")
        st.cache_data.clear()
        
        # Avanzar automáticamente al siguiente cliente si no estamos en el último
        if idx_actual + 1 < len(df_chofer):
            st.session_state["cliente_idx"] = idx_actual + 1
            st.query_params["cliente_idx"] = idx_actual + 1
            st.rerun()
            
    except Exception as err:
        st.error(f"Error al guardar datos: {err}")

# ---------------------------------------------------------
# NAVEGACIÓN MANUAL ENTRE CLIENTES
# ---------------------------------------------------------
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    if st.button("⬅️ Anterior") and idx_actual > 0:
        st.session_state["cliente_idx"] = idx_actual - 1
        st.query_params["cliente_idx"] = idx_actual - 1
        st.rerun()

with col2:
    if st.button("Siguiente ➡️") and idx_actual < len(df_chofer) - 1:
        st.session_state["cliente_idx"] = idx_actual + 1
        st.query_params["cliente_idx"] = idx_actual + 1
        st.rerun()

# Botón final al terminar el recorrido
if idx_actual == len(df_chofer) - 1:
    st.markdown("---")
    st.success("🎉 ¡Llegaste al último cliente del reparto!")
    if st.button("🏁 Finalizar Reparto y Salir"):
        st.query_params.clear()
        st.session_state.clear()
        st.rerun()
