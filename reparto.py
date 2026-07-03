import streamlit as st
import gspread
import json
from google.oauth2.service_account import Credentials

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Reparto Panadería", page_icon="🍞", layout="centered")

# Estilos visuales para la interfaz
st.markdown("""
<style>
    /* Ajustes generales */
    .stApp { max-width: 600px; margin: 0 auto; }
    
    /* Forzar que las columnas de los números NO se apilen nunca */
    [data-testid="column"] {
        width: calc(33.33% - 1rem) !important;
        flex: 1 1 calc(33.33% - 1rem) !important;
        min-width: 0 !important;
    }

    /* Asegurar que el contenedor de las columnas sea una fila */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        gap: 5px !important;
    }
    
    /* Botones más grandes para dedos */
    .stButton > button {
        height: 50px !important;
        width: 100% !important;
        font-size: 16px !important;
        font-weight: bold;
        padding: 0 !important;
    }
    
    /* Cajas con fuentes responsivas */
    .caja-saldos {
        background-color: #F3F4F6;
        padding: 10px;
        border-radius: 12px;
        text-align: center;
        font-size: 1.2rem !important;
        margin-bottom: 10px;
        border: 1px solid #E5E7EB;
    }
    .caja-deuda {
        background-color: #FEF2F2;
        padding: 10px;
        border-radius: 12px;
        text-align: center;
        font-size: 1.1rem !important;
        margin-bottom: 10px;
        border: 1px solid #FCA5A5;
    }

    /* Ajustes generales */
    .stApp { max-width: 600px; margin: 0 auto; }
    
    /* Botones más grandes para dedos */
    .stButton > button {
        height: 60px !important;
        font-size: 18px !important;
        font-weight: bold;
    }
    
    /* Cajas con fuentes responsivas */
    .caja-saldos {
        background-color: #F3F4F6;
        padding: 15px;
        border-radius: 12px;
        text-align: center;
        font-size: 1.5rem !important; /* Tamaño adaptable */
        margin-bottom: 15px;
        border: 1px solid #E5E7EB;
    }
    .caja-deuda {
        background-color: #FEF2F2;
        padding: 12px;
        border-radius: 12px;
        text-align: center;
        font-size: 1.2rem !important; /* Tamaño adaptable */
        margin-bottom: 15px;
        border: 1px solid #FCA5A5;
    }
    
    /* Ajustes específicos para móviles */
    @media only screen and (max-width: 600px) {
        .stButton > button {
            height: 55px !important;
            padding: 0 !important;
        }
        h1 { font-size: 24px !important; }
    }
</style>
""", unsafe_allow_html=True)

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

# Guardamos las hojas en la memoria interna para que NO ralenticen los clics de la calculadora
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

# --- 4. CARGA Y PROCESAMIENTO OPTIMIZADO (SÓLO UNA VEZ AL INICIAR) ---
if "data_clientes" not in st.session_state or "data_control" not in st.session_state or not st.session_state.mapping_zonas:
    with st.spinner("Sincronizando planillas con el servidor..."):
        try:
            st.session_state.data_clientes = st.session_state.hoja_clientes.get_all_records()
            st.session_state.data_control = st.session_state.control_hoja.get_all_records()
            
            # Procesamos el mapeo de zonas
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

# --- PANTALLA 1: SELECCIÓN DE REPARTO (ZONA P o C) ---
if st.session_state.reparto is None:
    st.title("🍞 Sistema de Reparto")
    st.subheader("Seleccioná la zona de salida")
    
    reparto_elegido = st.selectbox("Salida / Reparto:", ["P", "C"])
    
    if st.button("Iniciar Reparto", type="primary", use_container_width=True):
        st.session_state.reparto = reparto_elegido
        
        clientes_filtrados = []
        for row in st.session_state.data_control:
            nom_cliente = str(row.get('Cliente', '')).strip()
            if st.session_state.mapping_zonas.get(nom_cliente) == reparto_elegido:
                clientes_filtrados.append(row)
        
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
    
    # --- BUSCADOR DINÁMICO DE LA COLUMNA C (DEUDA ANTERIOR) ---
    keys_control = list(cliente_actual.keys())
    # Buscamos por nombre de columna o por defecto la tercera columna (Índice 2 = Columna C)
    key_deuda = next((k for k in keys_control if 'deuda' in k.lower() or 'anterior' in k.lower()), None)
    if not key_deuda and len(keys_control) > 2:
        key_deuda = keys_control[2]
        
    deuda_valor = cliente_actual.get(key_deuda, 0) if key_deuda else 0
    try:
        deuda_float = float(str(deuda_valor).replace(',', '.')) if deuda_valor else 0.0
    except ValueError:
        deuda_float = 0.0
    
    if st.button(f"⬅️ Cambiar Zona (Reparto {st.session_state.reparto})", use_container_width=True):
        st.session_state.reparto = None
        st.session_state.lista_filtrada = []
        if "data_clientes" in st.session_state: del st.session_state.data_clientes
        if "data_control" in st.session_state: del st.session_state.data_control
        st.rerun()
        
    st.markdown("<hr>", unsafe_allow_html=True)
    
    st.markdown(f"<h1 style='text-align: center; color: #1E3A8A; margin-bottom: 0px;'>{nombre_cliente}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: #4B5563; font-size: 16px; font-weight: bold;'>Orden de entrega: #{orden_recorrido}</p>", unsafe_allow_html=True)
    
    # Visualización de la Deuda Anterior (Columna C)
    st.markdown(f"""
    <div class='caja-deuda'>
        <span style='color: #DC2626; font-weight: bold;'>⚠️ Deuda Anterior: ${deuda_float:,.2f}</span>
    </div>
    """, unsafe_allow_html=True)
    
    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        st.button("◀️ Anterior", use_container_width=True, on_click=retroceder_cliente)
    with col_nav2:
        st.button("Siguiente ▶️", use_container_width=True, on_click=avanzar_cliente)
                
    st.markdown(f"<p style='text-align: center; color: #6B7280; font-size: 14px;'>Cliente {idx + 1} de {len(lista)}</p>", unsafe_allow_html=True)
    
    monto_texto = st.session_state.monto_calculadora if st.session_state.monto_calculadora != "" else "0"
    monto_float = float(monto_texto)
    
    # Caja de visualización formateada a un máximo de 2 decimales
    st.markdown(f"""
    <div class='caja-saldos'>
        <span style='color: #16A34A; font-weight: bold;'>Paga hoy: ${monto_float:,.2f}</span>
    </div>
    """, unsafe_allow_html=True)
    
    # --- CALCULADORA COMPLETAMENTE INSTANTÁNEA ---
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
    
    # --- PROCESO DE CARGA ÚNICO ---
    if st.button("🚚 CARGAR PAGO Y CONTINUAR", use_container_width=True, type="primary"):
        try:
            with st.spinner("Guardando pago en Google Sheets..."):
                celda_cliente = st.session_state.control_hoja.find(nombre_cliente, in_column=2)
                
                if celda_cliente:
                    fila = celda_cliente.row
                    columna_pagos = 12  # Columna L (Pagos)
                    
                    # Redondeamos a 2 decimales antes de impactar en Sheets
                    monto_final = round(monto_float, 2)
                    st.session_state.control_hoja.update_cell(fila, columna_pagos, monto_final)
                    st.toast(f"✅ ¡Pago de ${monto_final:.2f} guardado para {nombre_cliente}!", icon="💰")
                    
                    st.session_state.lista_filtrada[idx]["Pagos"] = monto_final
                    for r in st.session_state.data_control:
                        if str(r.get("Cliente")).strip() == nombre_cliente:
                            r["Pagos"] = monto_final
                    
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
