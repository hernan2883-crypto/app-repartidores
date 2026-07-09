import streamlit as st
import pandas as pd
import gspread
import datetime
import json  # <-- Librería necesaria para leer tu clave en limpio
import streamlit.components.v1 as components

# --- DETECCIÓN AUTOMÁTICA DEL DÍA REAL ---
dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
dia_actual = dias_semana[datetime.datetime.now().weekday()]

st.set_page_config(page_title="Reparto Pan", page_icon="🍞", layout="centered")

# --- CONEXIÓN A GOOGLE SHEETS ---
@st.cache_resource
def conectar_google_sheets():
    credenciales = json.loads(st.secrets["gcp_json_puro"])
    gc = gspread.service_account_from_dict(credenciales)
    sh = gc.open_by_key("10s3sTda68B_RAebXc91Ttl3Oa2Yy88EJ3psJUeJexcM")
    return sh

try:
    sh = conectar_google_sheets()
except Exception as e:
    st.error(f"Error de conexión con Google Sheets: {e}")
    st.stop()

# --- JAVASCRIPT: SELECCIÓN AUTOMÁTICA DE TEXTO AL TOCAR UN INPUT ---
components.html(f"""
<script>
const doc = window.parent.document;
if (!doc._globalFocusHandler) {{
    doc.addEventListener('focusin', (e) => {{
        if (e.target.tagName === 'INPUT') {{
            setTimeout(() => {{ e.target.select(); }}, 50);
        }}
    }});
    doc._globalFocusHandler = true;
}}
</script>
""", height=0)

# --- CSS: RESALTE DE CONTRASTE Y ANTI-TRADUCCIÓN ---
st.markdown("""
    <style>
    .block-container { padding: 10px !important; }
    
    /* 1. INPUT GIGANTE: Monto a Cobrar (TEXTO BLANCO FORZADO) */
    div[data-testid="stNumberInput"]:has(input[aria-label="Monto"]) div[data-baseweb="input"] {
        background-color: #27AE60 !important;
        border: 4px solid #219653 !important;
        border-radius: 15px !important;
        height: 90px !important;
    }
    div[data-testid="stNumberInput"]:has(input[aria-label="Monto"]) input {
        font-size: 45px !important;
        font-weight: 900 !important;
        text-align: center !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }
    div[data-testid="stNumberInput"]:has(input[aria-label="Monto"]) input:focus {
        background-color: #27AE60 !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }
    
    /* 2. CUADRITOS CHICOS: Fondo oscuro y texto BLANCO */
    div[data-testid="stNumberInput"]:not(:has(input[aria-label="Monto"])) div[data-baseweb="input"] {
        background-color: #34495E !important;
        border: 2px solid #2C3E50 !important;
        border-radius: 8px !important;
        height: 45px !important;
    }
    div[data-testid="stNumberInput"]:not(:has(input[aria-label="Monto"])) input {
        font-size: 16px !important;
        font-weight: 800 !important;
        text-align: center !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        padding: 0px !important;
    }
    div[data-testid="stNumberInput"]:not(:has(input[aria-label="Monto"])) input:focus {
        background-color: #34495E !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }
    button[aria-label="Step Up"], button[aria-label="Step Down"] { display: none !important; }
    </style>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN DE VARIABLES GLOBALES ---
if 'cliente_actual_idx' not in st.session_state: st.session_state.cliente_actual_idx = 0
if 'reparto_seleccionado' not in st.session_state: st.session_state.reparto_seleccionado = None
if 'dia_semana_reparto' not in st.session_state: st.session_state.dia_semana_reparto = dia_actual
if 'total_efectivo_caja' not in st.session_state: st.session_state.total_efectivo_caja = 0.0

# --- LÓGICA DE GUARDADO DE MONTO Y SUMA ---
def guardar_y_avanzar():
    idx = st.session_state.cliente_actual_idx
    cliente_actual = st.session_state.clientes_reparto.iloc[idx]
    clave_input = f"input_{cliente_actual['ID_Cliente']}"
    
    monto = st.session_state.get(clave_input)
    
    if monto is not None and monto > 0:
        try:
            ws = sh.worksheet("Control-Diario")
            fila_excel = int(cliente_actual['excel_row'])
            
            # Guardamos el monto tal cual lo escribís (entero o con coma)
            ws.update_cell(fila_excel, 12, monto)
            
            # Sumamos al acumulador en vivo
            st.session_state.total_efectivo_caja += float(monto)
            
            st.toast(f"✅ Guardado online: ${monto} - {cliente_actual['Cliente']}", icon="🍞")
            st.session_state.cliente_actual_idx += 1
            st.session_state.dia_semana_reparto = dia_actual
        except Exception as e:
            st.error(f"Error al guardar en Google Sheets: {e}")

# --- LÓGICA DE GUARDADO DE CANTIDADES EN LA HOJA DEL DÍA ---
def guardar_cantidad_dia(id_cliente, col_idx, key_name):
    val = st.session_state.get(key_name)
    dia = st.session_state.dia_semana_reparto
    if val is not None:
        try:
            ws = sh.worksheet(dia)
            celda = ws.find(str(id_cliente), in_column=1)
            
            if celda:
                ws.update_cell(celda.row, col_idx, val)
                st.toast(f"💾 Modificado en {dia}: {val}", icon="📦")
            else:
                st.error(f"No se encontró el ID {id_cliente} en la hoja {dia}")
        except Exception as e:
            st.error(f"Error al actualizar cantidad en la hoja {dia}: {e}")

# --- NAVEGACIÓN ---
if st.session_state.reparto_seleccionado is None:
    st.title("🍞 Selección de Reparto")
    if st.button("👨‍🍳 REPARTO P (Papá)", use_container_width=True): 
        st.session_state.reparto_seleccionado = "P"
        st.session_state.cliente_actual_idx = 0
        st.session_state.dia_semana_reparto = dia_actual
        if 'clientes_reparto' in st.session_state: del st.session_state.clientes_reparto
        st.rerun()
    if st.button("🚚 REPARTO C (Chelo)", use_container_width=True): 
        st.session_state.reparto_seleccionado = "C"
        st.session_state.cliente_actual_idx = 0
        st.session_state.dia_semana_reparto = dia_actual
        if 'clientes_reparto' in st.session_state: del st.session_state.clientes_reparto
        st.rerun()
else:
    if 'clientes_reparto' not in st.session_state:
        with st.spinner("Cargando datos desde Google Sheets..."):
            ws_control = sh.worksheet("Control-Diario")
            matriz_control = ws_control.get_all_values()
            df = pd.DataFrame(matriz_control[1:], columns=matriz_control[0])
            df['excel_row'] = df.index + 2
            
            matriz_clientes = sh.worksheet("Clientes").get_all_values()
            df_cli = pd.DataFrame(matriz_clientes[1:], columns=matriz_clientes[0])
            
            # Procesamiento de datos numéricos iniciales
            columnas_num = ['salida', 'Deuda Anterior', 'Saldo Nuevo', 'Cant_Pan', 'Cant_Miñon', 'Cant_Galletas', 'Cant_Figaza', 'Cant_Negritos', 'Cant_Facturas']
            for c in columnas_num:
                if c in df.columns:
                    # Reemplazamos puntos por nada si actúan como miles, o manejamos el texto limpio
                    df[c] = df[c].astype(str).str.replace('$', '', regex=False).str.strip()
                    df[c] = pd.to_numeric(df[c].str.replace(',', '.'), errors='coerce').fillna(0)

            st.session_state.clientes_reparto = df.merge(df_cli[['ID_Cliente', 'Zona / Reparto']], on='ID_Cliente').query(f"`Zona / Reparto` == '{st.session_state.reparto_seleccionado}'").sort_values('salida').reset_index(drop=True)

    idx = st.session_state.cliente_actual_idx
    total_clientes = len(st.session_state.clientes_reparto)

    if idx >= total_clientes:
        st.balloons()
        st.success("¡Reparto terminado!")
        
        st.markdown(f"""
        <div style="background-color:#FFF; padding:20px; border-radius:15px; border: 3px solid #27AE60; text-align:center; margin-top:15px; margin-bottom:15px;">
            <p style="margin:0; color:#2C3E50; font-size:18px; font-weight:bold;">💵 TOTAL EFECTIVO RECOLECTADO:</p>
            <h1 style="margin:5px 0 0 0; color:#27AE60; font-size:48px; font-weight:900;">${st.session_state.total_efectivo_caja:,.2f}</h1>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("⬅️ Revisar Último Cliente", use_container_width=True):
            st.session_state.cliente_actual_idx = total_clientes - 1
            st.session_state.dia_semana_reparto = dia_actual
            st.rerun()
        if st.button("🔄 Volver al Menú Principal (Reinicia Caja)", use_container_width=True): 
            st.session_state.reparto_seleccionado = None
            st.session_state.cliente_actual_idx = 0
            st.session_state.dia_semana_reparto = dia_actual
            st.session_state.total_efectivo_caja = 0.0
            if 'clientes_reparto' in st.session_state: del st.session_state.clientes_reparto
            st.rerun()
    else:
        cliente = st.session_state.clientes_reparto.iloc[idx]
        
        col_menu, col_orden = st.columns([1, 3])
        with col_menu:
            if st.button("🏠 Menú", use_container_width=True):
                st.session_state.reparto_seleccionado = None
                st.session_state.dia_semana_reparto = dia_actual
                if 'clientes_reparto' in st.session_state: del st.session_state.clientes_reparto
                st.rerun()
        with col_orden:
            st.markdown(f"<p style='text-align:right; color:#7F8C8D; font-weight:bold; margin-top:5px;'>Reparto {st.session_state.reparto_seleccionado} | Orden: #{int(cliente['salida'])}</p>", unsafe_allow_html=True)
        
        progreso = idx / total_clientes
        st.progress(progreso)
        st.markdown(f"<p style='text-align:center; font-size:12px; color:#7F8C8D; margin-top:-10px;'>Cliente {idx + 1} de {total_clientes}</p>", unsafe_allow_html=True)
        
        st.markdown(f"""
        <div style="background-color:#F8F9F9; padding:12px; border-radius:15px; border-left: 8px solid #E67E22; margin-bottom:10px;">
            <h2 style="margin:0; color:#2C3E50; font-size:24px;">{cliente['Cliente']}</h2>
            <p style="margin:2px 0 0 0; color:#95A5A6; font-size:13px;">ID: {cliente['ID_Cliente']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # --- CORRECCIÓN DE DECIMALES Y MULTIPLICADOR DE SALDO ---
        valor_base = float(cliente.get('Saldo Nuevo', 0.0))
        # Si el saldo quedó guardado como 66.3 cuando debería ser 66300, ajustamos la escala de miles.
        if 0 < valor_base < 1000 and '.' in str(cliente.get('Saldo Nuevo', '')):
            saldo_nuevo = valor_base * 1000
        else:
            saldo_nuevo = valor_base

        st.markdown(f"<div style='text-align:center; margin-bottom:10px;'><span style='font-size:14px; color:#7F8C8D;'>⚠️ SALDO NUEVO: </span><span style='color:#C0392B; font-size:20px; font-weight:900;'>${saldo_nuevo:,.2f}</span></div>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; font-size:16px; font-weight:bold; color:#27AE60; margin-bottom:2px;'>MONTO A COBRAR:</p>", unsafe_allow_html=True)
        
        # --- CAMBIO: PASADO A PASO ENTERO (Sin declarar decimales obligatorios al tipear) ---
        st.number_input(
            "Monto", 
            key=f"input_{cliente['ID_Cliente']}", 
            value=None, 
            step=1,              # <-- Permite poner números enteros de corrido (ej: 10200)
            format="%d",         # <-- Fuerza formato de número entero visualmente al escribir
            placeholder="", 
            label_visibility="collapsed",
            on_change=guardar_y_avanzar
        )
        
        col_ant, col_sig = st.columns(2)
        with col_ant:
            if idx > 0:
                if st.button("⬅️ Anterior", use_container_width=True):
                    st.session_state.cliente_actual_idx -= 1
                    st.session_state.dia_semana_reparto = dia_actual
                    st.rerun()
            else:
                st.button("⬅️ Inicio", disabled=True, use_container_width=True)
                
        with col_sig:
            if st.button("Saltar ⏭️", use_container_width=True):
                st.session_state.cliente_actual_idx += 1
                st.session_state.dia_semana_reparto = dia_actual
                st.rerun()
                
        st.markdown("<hr style='margin:15px 0;'>", unsafe_allow_html=True)
        
        st.markdown("<p style='font-size:14px; font-weight:bold; color:#34495E; margin-bottom:2px;'>📆 Día del Reparto:</p>", unsafe_allow_html=True)
        st.selectbox(
            "Día Selector",
            ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"],
            key="dia_semana_reparto",
            label_visibility="collapsed"
        )
        
        st.markdown("<p style='font-size:14px; font-weight:bold; color:#34495E; margin-top:10px; margin-bottom:5px;'>📦 Cantidades:</p>", unsafe_allow_html=True)
        
        p_pan = float(cliente['Cant_Pan'])
        p_min = float(cliente['Cant_Miñon'])
        p_gal = float(cliente['Cant_Galletas'])
        p_fig = float(cliente['Cant_Figaza'])
        p_neg = float(cliente['Cant_Negritos'])
        p_fac = int(cliente['Cant_Facturas'])
        
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        with col1:
            st.markdown("<p class='notranslate' translate='no' style='text-align:center; font-size:11px; font-weight:bold; margin-bottom:2px; color:#34495E;'>Pan</p>", unsafe_allow_html=True)
            st.number_input("Pan", key=f"pan_{cliente['ID_Cliente']}", value=p_pan, format="%.1f", label_visibility="collapsed", on_change=guardar_cantidad_dia, args=(cliente['ID_Cliente'], 3, f"pan_{cliente['ID_Cliente']}"))
            
        with col2:
            st.markdown("<p class='notranslate' translate='no' style='text-align:center; font-size:11px; font-weight:bold; margin-bottom:2px; color:#34495E;'>Miñones</p>", unsafe_allow_html=True)
            st.number_input("Miñones", key=f"minones_{cliente['ID_Cliente']}", value=p_min, format="%.1f", label_visibility="collapsed", on_change=guardar_cantidad_dia, args=(cliente['ID_Cliente'], 4, f"minones_{cliente['ID_Cliente']}"))
            
        with col3:
            st.markdown("<p class='notranslate' translate='no' style='text-align:center; font-size:11px; font-weight:bold; margin-bottom:2px; color:#34495E;'>Galletas</p>", unsafe_allow_html=True)
            st.number_input("Galletas", key=f"galletas_{cliente['ID_Cliente']}", value=p_gal, format="%.1f", label_visibility="collapsed", on_change=guardar_cantidad_dia, args=(cliente['ID_Cliente'], 5, f"galletas_{cliente['ID_Cliente']}"))
            
        with col4:
            st.markdown("<p class='notranslate' translate='no' style='text-align:center; font-size:11px; font-weight:bold; margin-bottom:2px; color:#34495E;'>Figazas</p>", unsafe_allow_html=True)
            st.number_input("Figazas", key=f"figaza_{cliente['ID_Cliente']}", value=p_fig, format="%.1f", label_visibility="collapsed", on_change=guardar_cantidad_dia, args=(cliente['ID_Cliente'], 6, f"figaza_{cliente['ID_Cliente']}"))
            
        with col5:
            st.markdown("<p class='notranslate' translate='no' style='text-align:center; font-size:11px; font-weight:bold; margin-bottom:2px; color:#34495E;'>Negritos</p>", unsafe_allow_html=True)
            st.number_input("Negritos", key=f"negrito_{cliente['ID_Cliente']}", value=p_neg, format="%.1f", label_visibility="collapsed", on_change=guardar_cantidad_dia, args=(cliente['ID_Cliente'], 7, f"negrito_{cliente['ID_Cliente']}"))
            
        with col6:
            st.markdown("<p class='notranslate' translate='no' style='text-align:center; font-size:11px; font-weight:bold; margin-bottom:2px; color:#34495E;'>Facturas</p>", unsafe_allow_html=True)
            st.number_input("Facturas", key=f"facturas_{cliente['ID_Cliente']}", value=p_fac, step=1, label_visibility="collapsed", on_change=guardar_cantidad_dia, args=(cliente['ID_Cliente'], 8, f"facturas_{cliente['ID_Cliente']}"))

        # --- CASILLERO BLANCO ABAJO DE TODO EN VIVO ---
        st.markdown("<br>", unsafe_allow_html=True)
        col_caja, col_clear = st.columns([3, 1])
        with col_caja:
            st.markdown(f"""
            <div style="background-color:#FFF; padding:10px; border-radius:10px; border: 2px solid #BDC3C7; text-align:center;">
                <span style="color:#7F8C8D; font-size:13px; font-weight:bold;">💵 TOTAL EN CAJA EN VIVO: </span>
                <span style="color:#2C3E50; font-size:18px; font-weight:900; margin-left:10px;">${st.session_state.total_efectivo_caja:,.2f}</span>
            </div>
            """, unsafe_allow_html=True)
        with col_clear:
            if st.button("❌ Vaciar Caja", use_container_width=True):
                st.session_state.total_efectivo_caja = 0.0
                st.rerun()
