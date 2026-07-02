import streamlit as st
import gspread
import json
from google.oauth2.service_account import Credentials

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Reparto Panadería", page_icon="🍞", layout="centered")

# Estilos visuales para la caja de saldos
st.markdown("""
<style>
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

# --- 2. CONEXIÓN AUTENTICADA (Hojas + Drive) ---
@st.cache_resource
def conectar_sheets():
    informacion = json.loads(st.secrets["gcp_json"])
    alcances = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credenciales = Credentials.from_service_account_info(informacion, scopes=alcances)
    return gspread.authorize(credenciales)

try:
    gc = conectar_sheets()
    doc = gc.open("Planilla_Maestra_Panaderia")
    hoja_clientes = doc.worksheet("Clientes")
    control_hoja = doc.worksheet("Control-Diario")
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

# --- 4. CARGA DE DATOS OPTIMIZADA (PROTECCIÓN CONTRA ERROR 429) ---
# Guardamos los datos en la memoria de la sesión para NO llamar a Google con cada clic del teclado
if "data_control" not in st.session_state:
    try:
        st.session_state.data_control = control_hoja.get_all_records()
    except Exception as e:
        st.error(f"Error al leer los datos de la planilla: {e}")
        st.stop()

data_control = st.session_state.data_control

# Extraemos los números o repartos únicos de la columna 'salida'
todas_salidas = sorted(list(set([str(row['salida']) for row in data_control if row.get('salida') != ''])))

# --- PANTALLA 1: SELECCIÓN DE REPARTO ---
if st.session_state.reparto is None:
    st.title("🍞 Sistema de Reparto")
    st.subheader("Seleccioná el reparto del día")
    
    reparto_elegido = st.selectbox("Salida / Reparto:", todas_salidas)
    
    if st.button("Iniciar Reparto", type="primary", use_container_width=True):
        st.session_state.reparto = reparto_elegido
        # Filtramos los clientes correspondientes
        st.session_state.lista_filtrada = [row for row in data_control if str(row.get('salida')) == reparto_elegido]
        st.session_state.idx_cliente = 0
        st.session_state.monto_calculadora = ""
        st.rerun()

# --- PANTALLA 2: CONTROL DE REPARTO CLIENTE POR CLIENTE ---
else:
    lista = st.session_state.lista_filtrada
    
    if not lista:
        st.warning(f"No se encontraron clientes para el reparto '{st.session_state.reparto}'")
        if st.button("Volver"):
            st.session_state.reparto = None
            st.rerun()
        st.stop()
        
    idx = st.session_state.idx_cliente
    if idx >= len(lista):
        idx = len(lista) - 1
    if idx < 0:
        idx = 0
    st.session_state.idx_cliente = idx
    
    cliente_actual = lista[idx]
    nombre_cliente = cliente_actual["Cliente"]
    
    if st.button(f"⬅️ Cambiar Reparto (Saliendo de {st.session_state.reparto})", use_container_width=True):
        st.session_state.reparto = None
        st.session_state.lista_filtrada = []
        # Al salir, limpiamos la memoria para que la próxima vez traiga datos frescos
        if "data_control" in st.session_state:
            del st.session_state.data_control
        st.rerun()
        
    st.markdown("<hr>", unsafe_allow_html=True)
    
    st.markdown(f"<h1 style='text-align: center; color: #1E3A8A; margin-bottom: 0px;'>{nombre_cliente}</h1>", unsafe_allow_html=True)
    
    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        if st.button("◀️ Anterior", use_container_width=True):
            if st.session_state.idx_cliente > 0:
                st.session_state.idx_cliente -= 1
                st.session_state.monto_calculadora = ""
                st.rerun()
    with col_nav2:
        if st.button("Siguiente ▶️", use_container_width=True):
            if st.session_state.idx_cliente < len(lista) - 1:
                st.session_state.idx_cliente += 1
                st.session_state.monto_calculadora = ""
                st.rerun()
                
    st.markdown(f"<p style='text-align: center; color: #6B7280; font-size: 14px;'>Cliente {idx + 1} de {len(lista)}</p>", unsafe_allow_html=True)
    
    monto_texto = st.session_state.monto_calculadora if st.session_state.monto_calculadora != "" else "0"
    monto_float = float(monto_texto)
    
    st.markdown(f"""
    <div class='caja-saldos'>
        <span style='color: #16A34A; font-weight: bold;'>Paga hoy: ${monto_float:,.2f}</span>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("1", use_container_width=True):
            st.session_state.monto_calculadora += "1"
            st.rerun()
        if st.button("4", use_container_width=True):
            st.session_state.monto_calculadora += "4"
            st.rerun()
        if st.button("7", use_container_width=True):
            st.session_state.monto_calculadora += "7"
            st.rerun()
        if st.button("⌫ Borrar", use_container_width=True):
            st.session_state.monto_calculadora = st.session_state.monto_calculadora[:-1]
            st.rerun()
            
    with col2:
        if st.button("2", use_container_width=True):
            st.session_state.monto_calculadora += "2"
            st.rerun()
        if st.button("5", use_container_width=True):
            st.session_state.monto_calculadora += "5"
            st.rerun()
        if st.button("8", use_container_width=True):
            st.session_state.monto_calculadora += "8"
            st.rerun()
        if st.button("0", use_container_width=True):
            st.session_state.monto_calculadora += "0"
            st.rerun()
            
    with col3:
        if st.button("3", use_container_width=True):
            st.session_state.monto_calculadora += "3"
            st.rerun()
        if st.button("6", use_container_width=True):
            st.session_state.monto_calculadora += "6"
            st.rerun()
        if st.button("9", use_container_width=True):
            st.session_state.monto_calculadora += "9"
            st.rerun()
        if st.button("C Limpiar", use_container_width=True):
            st.session_state.monto_calculadora = ""
            st.rerun()
            
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("🚚 CARGAR PAGO Y CONTINUAR", use_container_width=True, type="primary"):
        try:
            with st.spinner("Guardando pago en Google Sheets..."):
                celda_cliente = control_hoja.find(nombre_cliente, in_column=2)
                
                if celda_cliente:
                    fila = celda_cliente.row
                    columna_pagos = 12
                    
                    control_hoja.update_cell(fila, columna_pagos, monto_float)
                    st.toast(f"✅ ¡Pago de ${monto_float:.2f} guardado para {nombre_cliente}!", icon="💰")
                    
                    # Actualizamos el valor en nuestra lista en memoria para que no haga falta recargar todo desde Google
                    st.session_state.lista_filtrada[idx]["Pagos"] = monto_float
                    
                    if st.session_state.idx_cliente < len(lista) - 1:
                        st.session_state.idx_cliente += 1
                        st.session_state.monto_calculadora = ""
                    else:
                        st.balloons()
                        st.success("🎉 ¡Completaste todos los clientes de este reparto!")
                        if "data_control" in st.session_state:
                            del st.session_state.data_control
                    st.rerun()
                else:
                    st.error(f"No se encontró a '{nombre_cliente}' en la columna B de la planilla.")
        except Exception as e:
            st.error(f"Error crítico al guardar: {e}")
