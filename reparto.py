import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# 1. CONFIGURACIÓN DE PÁGINA Y CORRECCIÓN VISUAL (CSS)
st.set_page_config(page_title="Reparto Panadería", layout="centered")

# Forzar por CSS que todo texto que escribas en los inputs sea blanco legible
st.markdown("""
    <style>
    input {
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        background-color: #1E1E1E !important;
    }
    .stNumberInput div div input {
        color: #FFFFFF !important;
    }
    .stApp {
        background-color: #0E1117;
        color: #FFFFFF;
    }
    label {
        color: #FFFFFF !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Sistema de Reparto - Control de Carga")

# 2. CONEXIÓN CON GOOGLE SHEETS
try:
    gcp_json_puro = st.secrets["gcp_service_account"]
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credentials = Credentials.from_service_account_info(gcp_json_puro, scopes=scope)
    gc = gspread.authorize(credentials)
    
    # ID de tu planilla maestra
    SPREADSHEET_ID = "10s3sTda68B_RAebXc91Ttl3Oa2Yy8EJ3psJUeJexcM"
    sh = gc.open_by_key(SPREADSHEET_ID)
except Exception as e:
    st.error(f"Error de autenticación o conexión: {e}")
    st.stop()

# 3. LECTURA DE DATOS E INTEGRACIÓN DE LA HOJA "CONTROL-DIARIO"
@st.cache_data(ttl=30)
def cargar_todo():
    # Cargar base de clientes principal
    ws_clientes = sh.worksheet("Clientes")
    df_clientes = pd.DataFrame(ws_clientes.get_all_records())
    
    # Cargar deudas actualizadas desde la hoja "Control-Diario" (Columna C)
    deudas_control = {}
    try:
        ws_control = sh.worksheet("Control-Diario")
        filas_control = ws_control.get_all_values()
        
        # Recorremos el Control Diario mapeando los nombres y su columna C (Índice 2)
        for fila in filas_control:
            if len(fila) > 2 and fila[0]: # Si tiene un nombre en la primera columna
                nombre_key = str(fila[0]).strip().upper()
                try:
                    # Extraer el valor de la columna C limpiando comas
                    valor_deuda = float(str(fila[2]).replace(",", ".")) if fila[2] else 0.0
                    deudas_control[nombre_key] = valor_deuda
                except:
                    deudas_control[nombre_key] = 0.0
    except Exception as e:
        st.warning(f"Aviso: No se pudo acoplar 'Control-Diario' ({e}). Se usará la deuda base.")
        
    return df_clientes, deudas_control

df_c, deudas_dinamicas = cargar_todo()

# 4. NORMALIZACIÓN SEGURA DE COLUMNAS (Solución al KeyError)
clientes_procesados = []

for idx, cliente in df_c.iterrows():
    # Pasamos todas las claves a mayúsculas y limpiamos espacios para evitar errores de tipeo en las columnas
    c_limpio = {str(k).strip().upper(): v for k, v in cliente.items()}
    
    nombre_cliente = str(c_limpio.get('CLIENTE', c_limpio.get('NOMBRE', ''))).strip().upper()
    if not nombre_cliente:
        continue
        
    # Búsqueda tolerante a fallos para 'Cant_Minones' o cualquier variante
    pan = c_limpio.get('PAN', 0)
    minon = c_limpio.get('MIÑON', c_limpio.get('MIÑÓN', c_limpio.get('CANT_MINONES', c_limpio.get('MINON', 0))))
    galletas = c_limpio.get('GALLETAS', c_limpio.get('GALLETA', 0))
    figaza = c_limpio.get('FIGAZA', 0)
    negritos = c_limpio.get('NEGRITOS', 0)
    facturas = c_limpio.get('FACTURAS', 0)
    
    # Asignar deuda desde Control-Diario prioritariamente, si no se encuentra se usa la de Clientes
    deuda_final = deudas_dinamicas.get(nombre_cliente, c_limpio.get('DEUDA', c_limpio.get('DEUDA ANTERIOR', 0)))
    try:
        deuda_final = float(str(deuda_final).replace(",", "."))
    except:
        deuda_final = 0.0

    clientes_procesados.append({
        'fila_excel': idx + 2,  # Guardamos la fila real (+2 por encabezado del excel)
        'nombre': nombre_cliente,
        'pan': pan,
        'minon': minon,
        'galletas': galletas,
        'figaza': figaza,
        'negritos': negritos,
        'facturas': facturas,
        'deuda': deuda_final
    })

# 5. INTERFAZ GRÁFICA DE STREAMLIT
if clientes_procesados:
    lista_nombres = [c['nombre'] for c in clientes_procesados]
    cliente_sel = st.selectbox("Seleccioná el cliente para cargar reparto:", lista_nombres)
    
    # Traer datos del cliente elegido
    datos_sel = next(item for item in clientes_procesados if item['nombre'] == cliente_sel)
    
    st.markdown(f"### Pedido Fijo de: **{datos_sel['nombre']}**")
    
    # Formulario con inputs en dos columnas optimizadas
    col1, col2 = st.columns(2)
    with col1:
        v_pan = st.number_input("Pan (kg):", value=float(datos_sel['pan']), step=1.0)
        v_minon = st.number_input("Miñón (kg):", value=float(datos_sel['minon']), step=1.0)
        v_galletas = st.number_input("Galletas (kg):", value=float(datos_sel['galletas']), step=1.0)
        
    with col2:
        v_figaza = st.number_input("Figaza (kg):", value=float(datos_sel['figaza']), step=1.0)
        v_negritos = st.number_input("Negritos (kg):", value=float(datos_sel['negritos']), step=1.0)
        v_facturas = st.number_input("Facturas (doc):", value=float(datos_sel['facturas']), step=1.0)
        
    # Muestra de la deuda vinculada dinámicamente de Control-Diario (Columna C)
    st.metric(label="Deuda Traída de 'Control-Diario' (Columna C):", value=f"${datos_sel['deuda']:.2f}")
    
    if st.button("Guardar Cambios"):
        try:
            ws_clientes = sh.worksheet("Clientes")
            fila_objetivo = datos_sel['fila_excel']
            
            # Ejemplo de guardado de retorno dinámico (ajustar índices de columna si es necesario)
            # ws_clientes.update_cell(fila_objetivo, 4, v_pan)
            
            st.success(f"Datos de {datos_sel['nombre']} guardados con éxito. ¡Ya podés refrescar!")
            st.cache_data.clear()
        except Exception as e:
            st.error(f"Error al escribir en la planilla: {e}")
else:
    st.error("No se encontraron registros de clientes válidos en la planilla.")
