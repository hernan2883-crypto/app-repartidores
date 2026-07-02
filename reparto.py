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
if "mapping_zonas" not in st.session_state:
    st.session_state.mapping_zonas = {}

# --- 4. CARGA Y PROCESAMIENTO OPTIMIZADO (SÓLO UNA VEZ) ---
if "data_clientes" not in st.session_state or "data_control" not in st.session_state or not st.session_state.mapping_zonas:
    with st.spinner("Sincronizando planillas con el servidor..."):
        try:
            st.session_state.data_clientes = hoja_clientes.get_all_records()
            st.session_state.data_control = control_hoja.get_all_records()
            
            # Procesamos el mapeo de zonas ACÁ una sola vez para evitar lentitud
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

# --- 5. FUNCIONES CALLBACKS (PROCESAMIENTO INSTANTÁNEO) ---
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

# --- PANTALLA 1: SELECCIÓN DE REPARTO (ZONA P o C) ---
if st.session_state.reparto is None:
    st.title("🍞 Sistema de Reparto")
    st.subheader("Seleccioná la zona de salida")
    
    reparto_elegido = st.selectbox("Salida / Reparto:", ["P", "C"])
    
    if st.button("Iniciar Reparto", type="primary", use_container_width=True):
        st.session_state.reparto = reparto_elegido
        
        # Filtramos rápido usando el mapa en memoria
        clientes_filtrados = []
        for row in st.session_state.data_control:
            nom_cliente = str(row.get('Cliente', '')).strip()
            if st.session_state.mapping_zonas.get(nom_cliente) == reparto_elegido:
                clientes_filtrados.append(row)
        
        # Ordenamos por número de salida (Columna N)
        def obtener_orden_salida(row):
            val = str(row.get('salida', '')).strip()
            try:
                return int(val)
            except ValueError:
                return 9999
        
        st.session_state.lista_filtrada = sorted(clientes_filtrados, key=obtener_orden_salida)
        st.session_state.idx_cliente = 0
        st.session_state.monto_calculadora = ""
        st.rerun()

# --- PANTALLA 2: CONTROL DE REPARTO CLIENTE POR CLIENTE ---
else:
    lista = st.session_state.lista_filtrada
    
    if not lista:
        st.warning(f"No se encontraron clientes asignados a la zona '{st.session_state.reparto}' en Control-Diario.")
        if st.button("Volver"):
            st.session_state.reparto = None
            st.rerun()
        st.stop()
        
    idx = st.session_state.idx_cliente
    if idx >= len(lista): idx = len(lista) - 1
    if idx < 0: idx = 0
    st.session_state.idx_cliente = idx
    
    cliente_actual = lista[idx]
    nombre_cliente = cliente_actual["Cliente"]
    orden_recorrido = cliente_actual.get("salida", "-")
    
    if st.button(f"⬅️ Cambiar Zona (Saliendo de Reparto {st.session_state.reparto})", use_container_width=True):
        st.session_state.reparto = None
        st.session_state.lista_filtrada = []
        if "data_clientes" in st.session_state: del st.session_state.data_clientes
        if "data_control" in st.session_state: del st.session_state.data_control
        st.rerun()
        
    st.markdown("<hr>", unsafe_allow_html=True)
    
    st.markdown(f"<h1 style='text-align: center; color: #1E3A8A; margin-bottom: 0px;'>{nombre_cliente}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: #4B5563; font-size: 16px; font-weight: bold;'>Orden de entrega: #{orden_recorrido}</p>", unsafe_allow_html=True)
    
    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        st.button("◀️ Anterior", use_container_width=True, on_click=retroceder_cliente)
    with col_nav2:
        st.button("Siguiente ▶️", use_container_width=True, on_click=avanzar_cliente)
                
    st.markdown(f"<p style='text-align: center; color: #6B7280; font-size: 14px;'>Cliente {idx + 1} de {len(lista)} de la zona {st.session_state.reparto}</p>", unsafe_allow_html=True)
    
    monto_texto = st.session_state.monto_calculadora if st.session_state.monto_calculadora != "" else "0"
    monto_float = float(monto_texto)
    
    st.markdown(f"""
    <div class='caja-saldos'>
        <span style='color: #16A34A; font-weight: bold;'>Paga hoy: ${monto_float:,.2f}</span>
    </div>
    """, unsafe_allow_html=True)
    
    # --- CALCULADORA ULTRA-RÁPIDA (CON CALLBACKS) ---
    col1, col2, col3 = st.columns(3)
    with col1:
        st.button("1", use_container_width=True, on_click=click_numero, args=("1",))
        st.button("4", use_container_width=True, on_click=click_numero, args=("4",))
        st.button("7", use_container_width=True, on_click=click_numero, args=("7",))
        st.button("⌫ Borrar", use_container_width=True, on_click=click_borrar)
            
    with col2:
        st.button("2", use_container_width=True, on_click=click_numero, args=("2",))
        st.button("5", use_container_width=True, on_click=click_numero, args=("5",))
        st.button("8", use_container_width=True, on_click=click_numero, args=("8",))
        st.button("0", use_container_width=True, on_click=click_numero, args=("0",))
            
    with col3:
        st.button("3", use_container_width=True, on_click=click_numero, args=("3",))
        st.button("6", use_container_width=True, on_click=click_numero, args=("6",))
        st.button("9", use_container_width=True, on_click=click_numero, args=("9",))
        st.button("C Limpiar", use_container_width=True, on_click=click_limpiar)
            
    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- ESTE BOTÓN HACE TODO EL TRABAJO PESADO ---
    if st.button("🚚 CARGAR PAGO Y CONTINUAR", use_container_width=True, type="primary"):
        try:
            with st.spinner("Guardando pago en Google Sheets..."):
                celda_cliente = control_hoja.find(nombre_cliente, in_column=2)
                
                if celda_cliente:
                    fila = celda_cliente.row
                    columna_pagos = 12  # Columna L (Pagos)
                    
                    # Se sube el número completo recién acá
                    control_hoja.update_cell(fila, columna_pagos, monto_float)
                    st.toast(f"✅ ¡Pago de ${monto_float:.2f} guardado para {nombre_cliente}!", icon="💰")
                    
                    st.session_state.lista_filtrada[idx]["Pagos"] = monto_float
                    for r in st.session_state.data_control:
                        if str(r.get("Cliente")).strip() == nombre_cliente:
                            r["Pagos"] = monto_float
                    
                    if st.session_state.idx_cliente < len(lista) - 1:
                        st.session_state.idx_cliente += 1
                        st.session_state.monto_calculadora = ""
                    else:
                        st.balloons()
                        st.success("🎉 ¡Completaste todos los clientes de este reparto!")
                        if "data_clientes" in st.session_state: del st.session_state.data_clientes
                        if "data_control" in st.session_state: del st.session_state.data_control
                    st.rerun()
                else:
                    st.error(f"No se encontró a '{nombre_cliente}' en la columna B de Control-Diario.")
        except Exception as e:
            st.error(f"Error crítico al guardar: {e}")
