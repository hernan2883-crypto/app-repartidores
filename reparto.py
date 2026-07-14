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
if 'repartidor_nombre' not in st.session_state: st.session_state.repartidor_nombre = None
if 'dia_semana_reparto' not in st.session_state: st.session_state.dia_semana_reparto = dia_actual
if 'total_efectivo_caja' not in st.session_state: st.session_state.total_efectivo_caja = 0.0
if 'col_pago_name' not in st.session_state: st.session_state.col_pago_name = None

# --- LÓGICA DE GUARDADO DE MONTO POR BOTÓN CON MATEMÁTICA EN VIVO ---
def guardar_y_avanzar_pago():
    idx = st.session_state.cliente_actual_idx
    cliente_actual = st.session_state.clientes_reparto.iloc[idx]
    clave_input = f"input_{cliente_actual['ID_Cliente']}"
    col_pago = st.session_state.col_pago_name
    
    monto = st.session_state.get(clave_input)
    monto_val = float(monto) if monto is not None else 0.0
    
    try:
        ws = sh.worksheet("Control-Diario")
        fila_excel = int(cliente_actual['excel_row'])
        
        # Guardamos el monto en Google Sheets (Columna 12)
        ws.update_cell(fila_excel, 12, monto_val)
        
        # Modificamos el DataFrame local al instante para impacto inmediato en pantalla
        st.session_state.clientes_reparto.at[idx, col_pago] = monto_val
        
        # Recalculamos el acumulador de caja sumando en vivo la columna del reparto actual
        st.session_state.total_efectivo_caja = float(st.session_state.clientes_reparto[col_pago].sum())
        
        st.toast(f"✅ Pago cargado: ${monto_val} - {cliente_actual['Cliente']}", icon="🍞")
        st.session_state.cliente_actual_idx += 1
        st.session_state.dia_semana_reparto = dia_actual
    except Exception as e:
        st.error(f"Error al guardar en Google Sheets: {e}")

# --- LÓGICA CENTRALIZADA PARA GUARDAR TODAS LAS CANTIDADES DEL PEDIDO ---
def guardar_todos_los_cambios_productos(cliente):
    id_cliente = cliente['ID_Cliente']
    dia = st.session_state.dia_semana_reparto
    try:
        ws = sh.worksheet(dia)
        celda = ws.find(str(id_cliente), in_column=1)
        
        if celda:
            val_pan = st.session_state.get(f"pan_{id_cliente}", 0.0)
            val_min = st.session_state.get(f"minones_{id_cliente}", 0.0)
            val_gal = st.session_state.get(f"galletas_{id_cliente}", 0.0)
            val_fig = st.session_state.get(f"figaza_{id_cliente}", 0.0)
            val_neg = st.session_state.get(f"negrito_{id_cliente}", 0.0)
            val_fac = st.session_state.get(f"facturas_{id_cli}", 0)
            
            # Guardamos secuencialmente los 6 productos de la fila (Columnas 3 a 8)
            valores = [val_pan, val_min, val_gal, val_fig, val_neg, val_fac]
            for i, val in enumerate(valores, start=3):
                ws.update_cell(celda.row, i, val)
            
            # Actualizamos localmente el DataFrame para que refleje los cambios al instante
            idx = st.session_state.cliente_actual_idx
            st.session_state.clientes_reparto.at[idx, 'Cant_Pan'] = val_pan
            st.session_state.clientes_reparto.at[idx, 'Cant_Miñon'] = val_min
            st.session_state.clientes_reparto.at[idx, 'Cant_Galletas'] = val_gal
            st.session_state.clientes_reparto.at[idx, 'Cant_Figaza'] = val_fig
            st.session_state.clientes_reparto.at[idx, 'Cant_Negritos'] = val_neg
            st.session_state.clientes_reparto.at[idx, 'Cant_Facturas'] = val_fac
            
            st.toast(f"💾 Cambios guardados en pestaña {dia}", icon="📦")
        else:
            st.error(f"No se encontró el ID {id_cliente} en la hoja {dia}")
    except Exception as e:
        st.error(f"Error al actualizar cantidades en {dia}: {e}")

# --- LÓGICA DE GUARDADO EN VIVO PARA BOLSAS (COLUMNA P = 16) ---
def guardar_bolsas_control_diario(fila_excel, nuevo_valor):
    try:
        ws = sh.worksheet("Control-Diario")
        ws.update_cell(fila_excel, 16, nuevo_valor)  # Columna P es la número 16
        st.toast(f"🎒 Bolsas actualizadas online: {nuevo_valor}", icon="📦")
    except Exception as e:
        st.error(f"Error al guardar bolsas en Control-Diario: {e}")

# --- NAVEGACIÓN Y ACCESO POR CÓDIGO ---
if st.session_state.reparto_seleccionado is None:
    st.title("🔐 Acceso Repartidores")
    st.markdown("### Ingresá tu código de seguridad para iniciar:")
    
    # Campo de password
    codigo_ingresado = st.text_input("Código", type="password", label_visibility="collapsed", key="login_codigo")
    
    if st.button("Ingresar 🔓", use_container_width=True, type="primary"):
        if codigo_ingresado:
            try:
                with st.spinner("Validando código con la planilla..."):
                    # Leemos la nueva pestaña de seguridad
                    ws_rep = sh.worksheet("Repartidores")
                    matriz_rep = ws_rep.get_all_values()
                    df_rep = pd.DataFrame(matriz_rep[1:], columns=matriz_rep[0])
                    
                    # Limpieza rápida por si hay espacios
                    df_rep.columns = df_rep.columns.str.strip()
                    df_rep['Codigo'] = df_rep['Codigo'].astype(str).str.strip()
                    df_rep['Reparto'] = df_rep['Reparto'].astype(str).str.strip()
                    df_rep['Repartidor'] = df_rep['Repartidor'].astype(str).str.strip()
                    
                    # Buscamos coincidencia exacta de código
                    match = df_rep[df_rep['Codigo'] == str(codigo_ingresado).strip()]
                    
                    if not match.empty:
                        repartidor_info = match.iloc[0]
                        
                        # Guardamos en sesión el reparto y el nombre real del chofer
                        st.session_state.reparto_seleccionado = repartidor_info['Reparto']
                        st.session_state.repartidor_nombre = repartidor_info['Repartidor']
                        st.session_state.cliente_actual_idx = 0
                        st.session_state.dia_semana_reparto = dia_actual
                        if 'clientes_reparto' in st.session_state: del st.session_state.clientes_reparto
                        
                        st.success(f"🔓 ¡Acceso correcto! Bienvenido {repartidor_info['Repartidor']}")
                        st.rerun()
                    else:
                        st.error("❌ Código incorrecto. Verificá los datos.")
            except Exception as e:
                st.error(f"Error al verificar seguridad: {e}")
                st.info("💡 Asegurate de que la pestaña 'Repartidores' exista en el Excel y tenga las columnas: Repartidor, Codigo, Reparto")
        else:
            st.warning("⚠️ Por favor, escribí un código.")
else:
    if 'clientes_reparto' not in st.session_state:
        with st.spinner("Cargando datos desde Google Sheets..."):
            ws_control = sh.worksheet("Control-Diario")
            matriz_control = ws_control.get_all_values()
            df = pd.DataFrame(matriz_control[1:], columns=matriz_control[0])
            df['excel_row'] = df.index + 2
            
            # Detectamos el nombre real de la columna 12 de pagos
            col_pago_name = matriz_control[0][11]
            st.session_state.col_pago_name = col_pago_name
            
            matriz_clientes = sh.worksheet("Clientes").get_all_values()
            df_cli = pd.DataFrame(matriz_clientes[1:], columns=matriz_clientes[0])
            
            # Procesamiento de datos numéricos iniciales (Agregamos la columna de PAGO dinámica)
            columnas_num = ['salida', 'Deuda Anterior', 'Saldo Nuevo', 'Cant_Pan', 'Cant_Miñon', 'Cant_Galletas', 'Cant_Figaza', 'Cant_Negritos', 'Cant_Facturas', 'BOLSAS', col_pago_name]
            for c in columnas_num:
                if c in df.columns:
                    df[c] = df[c].astype(str).str.replace('$', '', regex=False).str.strip()
                    df[c] = pd.to_numeric(df[c].str.replace(',', '.'), errors='coerce').fillna(0)

            df_filtrado = df.merge(df_cli[['ID_Cliente', 'Zona / Reparto']], on='ID_Cliente').query(f"`Zona / Reparto` == '{st.session_state.reparto_seleccionado}'").sort_values('salida').reset_index(drop=True)
            st.session_state.clientes_reparto = df_filtrado
            
            # --- LÓGICA DE MEMORIA INTELIGENTE (AUTO-RESUME) ---
            # 1. Sumamos en vivo todo lo que ya se cobró efectivamente en este reparto
            st.session_state.total_efectivo_caja = float(df_filtrado[col_pago_name].sum())
            
            # 2. Posicionamos automáticamente en el primer cliente que tenga el casillero de pago en 0
            clientes_sin_pago = df_filtrado[df_filtrado[col_pago_name] == 0]
            if not clientes_sin_pago.empty:
                st.session_state.cliente_actual_idx = int(clientes_sin_pago.index[0])
            else:
                # Si todos ya pagaron, lo dejamos al final en la pantalla de meta cumplida
                st.session_state.cliente_actual_idx = len(df_filtrado)

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
        if st.button("🔄 Salir de la Sesión (Bloquear App)", use_container_width=True): 
            st.session_state.reparto_seleccionado = None
            st.session_state.repartidor_nombre = None
            st.session_state.cliente_actual_idx = 0
            st.session_state.dia_semana_reparto = dia_actual
            st.session_state.total_efectivo_caja = 0.0
            if 'clientes_reparto' in st.session_state: del st.session_state.clientes_reparto
            st.rerun()
    else:
        cliente = st.session_state.clientes_reparto.iloc[idx]
        
        col_menu, col_orden = st.columns([1.2, 2.8])
        with col_menu:
            if st.button("🔒 Salir", use_container_width=True):
                st.session_state.reparto_seleccionado = None
                st.session_state.repartidor_nombre = None
                st.session_state.dia_semana_reparto = dia_actual
                if 'clientes_reparto' in st.session_state: del st.session_state.clientes_reparto
                st.rerun()
        with col_orden:
            nombre_repartidor = st.session_state.get('repartidor_nombre', st.session_state.reparto_seleccionado)
            st.markdown(f"<p style='text-align:right; color:#7F8C8D; font-weight:bold; margin-top:5px;'>🚚 {nombre_repartidor} | Orden: #{int(cliente['salida'])}</p>", unsafe_allow_html=True)
        
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
        if 0 < valor_base < 1000 and '.' in str(cliente.get('Saldo Nuevo', '')):
            saldo_nuevo = valor_base * 1000
        else:
            saldo_nuevo = valor_base

        # --- MATEMÁTICA Y RESPUESTA INMEDIATA EN PANTALLA ---
        col_pago = st.session_state.col_pago_name
        pago_registrado = float(cliente.get(col_pago, 0.0))
        saldo_restante = saldo_nuevo - pago_registrado

        st.markdown(f"<div style='text-align:center; margin-bottom:4px;'><span style='font-size:14px; color:#7F8C8D;'>⚠️ DEUDA ORIGINAL: </span><span style='color:#C0392B; font-size:20px; font-weight:900;'>${saldo_nuevo:,.2f}</span></div>", unsafe_allow_html=True)
        if pago_registrado > 0:
            st.markdown(f"<div style='text-align:center; margin-bottom:4px;'><span style='font-size:14px; color:#27AE60;'>💵 PAGO REGISTRADO: </span><span style='color:#27AE60; font-size:20px; font-weight:900;'>${pago_registrado:,.2f}</span></div>", unsafe_allow_html=True)
            st.markdown(f"<div style='text-align:center; margin-bottom:10px;'><span style='font-size:14px; color:#7F8C8D;'>📉 SALDO RESTANTE: </span><span style='color:#2980B9; font-size:20px; font-weight:900;'>${saldo_restante:,.2f}</span></div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='text-align:center; margin-bottom:10px;'><span style='font-size:14px; color:#7F8C8D;'>📉 SALDO RESTANTE: </span><span style='color:#C0392B; font-size:20px; font-weight:900;'>${saldo_nuevo:,.2f}</span></div>", unsafe_allow_html=True)

        st.markdown("<p style='text-align:center; font-size:16px; font-weight:bold; color:#27AE60; margin-bottom:2px;'>MONTO A COBRAR:</p>", unsafe_allow_html=True)
        
        # Seteamos el estado del input basado en si ya tenía un pago guardado (útil al ir hacia atrás)
        clave_pago_input = f"input_{cliente['ID_Cliente']}"
        if clave_pago_input not in st.session_state:
            st.session_state[clave_pago_input] = int(pago_registrado) if pago_registrado > 0 else None

        # --- INPUT SIN EVENTO AUTO-SUBMIT (Eliminado on_change) ---
        st.number_input(
            "Monto", 
            key=clave_pago_input, 
            step=1,              
            format="%d",         
            placeholder="", 
            label_visibility="collapsed"
        )
        
        # --- BOTÓN EXPLÍCITO PARA CARGAR EL PAGO ---
        if st.button("💰 CARGAR PAGO Y AVANZAR", use_container_width=True, type="primary"):
            guardar_y_avanzar_pago()
            st.rerun()
        
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
        
        id_cli = cliente['ID_Cliente']
        # Inicializamos en session_state las variables de productos para que no se pisen
        if f"pan_{id_cli}" not in st.session_state: st.session_state[f"pan_{id_cli}"] = float(cliente['Cant_Pan'])
        if f"minones_{id_cli}" not in st.session_state: st.session_state[f"minones_{id_cli}"] = float(cliente['Cant_Miñon'])
        if f"galletas_{id_cli}" not in st.session_state: st.session_state[f"galletas_{id_cli}"] = float(cliente['Cant_Galletas'])
        if f"figaza_{id_cli}" not in st.session_state: st.session_state[f"figaza_{id_cli}"] = float(cliente['Cant_Figaza'])
        if f"negrito_{id_cli}" not in st.session_state: st.session_state[f"negrito_{id_cli}"] = float(cliente['Cant_Negritos'])
        if f"facturas_{id_cli}" not in st.session_state: st.session_state[f"facturas_{id_cli}"] = int(cliente['Cant_Facturas'])

        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        # --- PRODUCTOS SIN GUARDADO AUTOMÁTICO (Eliminado on_change) ---
        with col1:
            st.markdown("<p class='notranslate' translate='no' style='text-align:center; font-size:11px; font-weight:bold; margin-bottom:2px; color:#34495E;'>Pan</p>", unsafe_allow_html=True)
            st.number_input("Pan", key=f"pan_{id_cli}", format="%.1f", label_visibility="collapsed")
            
        with col2:
            st.markdown("<p class='notranslate' translate='no' style='text-align:center; font-size:11px; font-weight:bold; margin-bottom:2px; color:#34495E;'>Miñones</p>", unsafe_allow_html=True)
            st.number_input("Miñones", key=f"minones_{id_cli}", format="%.1f", label_visibility="collapsed")
            
        with col3:
            st.markdown("<p class='notranslate' translate='no' style='text-align:center; font-size:11px; font-weight:bold; margin-bottom:2px; color:#34495E;'>Galletas</p>", unsafe_allow_html=True)
            st.number_input("Galletas", key=f"galletas_{id_cli}", format="%.1f", label_visibility="collapsed")
            
        with col4:
            st.markdown("<p class='notranslate' translate='no' style='text-align:center; font-size:11px; font-weight:bold; margin-bottom:2px; color:#34495E;'>Figazas</p>", unsafe_allow_html=True)
            st.number_input("Figazas", key=f"figaza_{id_cli}", format="%.1f", label_visibility="collapsed")
            
        with col5:
            st.markdown("<p class='notranslate' translate='no' style='text-align:center; font-size:11px; font-weight:bold; margin-bottom:2px; color:#34495E;'>Negritos</p>", unsafe_allow_html=True)
            st.number_input("Negritos", key=f"negrito_{id_cli}", format="%.1f", label_visibility="collapsed")
            
        with col6:
            st.markdown("<p class='notranslate' translate='no' style='text-align:center; font-size:11px; font-weight:bold; margin-bottom:2px; color:#34495E;'>Facturas</p>", unsafe_allow_html=True)
            st.number_input("Facturas", key=f"facturas_{id_cli}", step=1, label_visibility="collapsed")

        # --- BOTÓN EXPLÍCITO PARA GUARDAR EL PEDIDO DE MERCADERÍA ---
        if st.button("💾 GUARDAR CAMBIOS EN PEDIDO", use_container_width=True):
            guardar_todos_los_cambios_productos(cliente)
            st.rerun()

        # --- SECCIÓN DE BOLSAS CON BOTONES MÁS / MENOS (SIN TECLADO TÁCTIL) ---
        st.markdown("<p style='font-size:14px; font-weight:bold; color:#34495E; margin-top:15px; margin-bottom:5px;'>🎒 Control de Bolsas (Sin Teclado):</p>", unsafe_allow_html=True)
        
        key_bolsas = f"bolsas_{id_cli}"
        if key_bolsas not in st.session_state:
            try:
                st.session_state[key_bolsas] = int(float(cliente.get('BOLSAS', 0)))
            except:
                st.session_state[key_bolsas] = 0

        # Diseño de botonera en 3 columnas: [ ➖ ] [ Número Grande ] [ ➕ ]
        col_b_menos, col_b_val, col_b_mas = st.columns([1, 1, 1])
        
        with col_b_menos:
            if st.button("➖", key=f"btn_menos_{id_cli}", use_container_width=True):
                st.session_state[key_bolsas] -= 1
                guardar_bolsas_control_diario(int(cliente['excel_row']), st.session_state[key_bolsas])
                st.rerun()
                
        with col_b_val:
            st.markdown(f"""
            <div style="background-color:#FFFFFF; border:2px solid #BDC3C7; border-radius:8px; height:38px; display:flex; align-items:center; justify-content:center;">
                <h3 style="margin:0; color:#2C3E50; font-weight:900; text-align:center; font-size:20px;">{st.session_state[key_bolsas]}</h3>
            </div>
            """, unsafe_allow_html=True)
            
        with col_b_mas:
            if st.button("➕", key=f"btn_mas_{id_cli}", use_container_width=True):
                st.session_state[key_bolsas] += 1
                guardar_bolsas_control_diario(int(cliente['excel_row']), st.session_state[key_bolsas])
                st.rerun()

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
