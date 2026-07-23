import streamlit as st 
import pandas as pd
from datetime import datetime 
from fpdf import FPDF 
from streamlit_gsheets import GSheetsConnection
import io

# ------- CONFIGURACIÓN DE PÁGINA ---------
st.set_page_config(
    page_title="Control de Inventario GCM", 
    page_icon="📦",
    layout="centered",
    initial_sidebar_state="expanded"
) 

# 🎨 CSS PERSONALIZADO PARA LAS TABLAS
st.markdown("""
    <style>
    [data-testid="stDataFrame"] div[data-testid="stTable"] td,
    .stDataFrame td, div[data-baseweb="datatable"] div {
        white-space: normal !important;
        word-wrap: break-word !important;
        height: auto !important;
    }
    </style>
""", unsafe_allow_html=True)

# --------INTERFAZ / LOGO SUPERIOR DERECHO---------- 
col1, col2 = st.columns([4, 1])
with col2:
    st.image("LOGOGCM.jpeg", width=140)

# 🔐 USUARIOS AUTORIZADOS
USUARIOS = {
    "zaid": "2010",
    "jdiaz": "1978",
    "ccdiazj": "1974",
    "gael": "2003",
    "monica": "2026",
    "sergio": "sergio2026*"
}

# 🔐 FUNCIÓN LOGIN
def login():
    st.title("🔐 Iniciar sesión")
    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Entrar"):
        if usuario in USUARIOS and USUARIOS[usuario] == password:
            st.session_state["autenticado"] = True
            st.session_state["usuario"] = usuario
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")

# 🔒 CONTROL DE SESIÓN
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    login()
    st.stop()

# 🔓 BOTÓN DE LOGOUT (SIDEBAR)
st.sidebar.write(f"👤 Usuario: {st.session_state['usuario']}")
if st.sidebar.button("🔓 Cerrar sesión"):
    st.session_state["autenticado"] = False
    st.rerun()

# -------Conexión a Google Sheets--------- 
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_inventario_dataframe(): 
    try:
        df = conn.read(worksheet="Productos", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=["PRODUCTO", "CANTIDAD_TOTAL", "CANTIDAD_ABIERTOS", "ALMACEN", "FECHA_INGRESO"])
        
        # Limpiar espacios y poner en mayúsculas los nombres de las columnas
        df.columns = df.columns.astype(str).str.strip().str.upper()
        
        # Compatibilidad si en tu hoja de Excel dice CANTIDAD_ACTUAL en vez de CANTIDAD_TOTAL
        if "CANTIDAD_ACTUAL" in df.columns and "CANTIDAD_TOTAL" not in df.columns:
            df.rename(columns={"CANTIDAD_ACTUAL": "CANTIDAD_TOTAL"}, inplace=True)
            
        if "PRODUCTO" not in df.columns:
            return pd.DataFrame(columns=["PRODUCTO", "CANTIDAD_TOTAL", "CANTIDAD_ABIERTOS", "ALMACEN", "FECHA_INGRESO"])
        
        # Rellenar columnas faltantes si no existen
        if "CANTIDAD_TOTAL" not in df.columns:
            df["CANTIDAD_TOTAL"] = 0
        if "CANTIDAD_ABIERTOS" not in df.columns:
            df["CANTIDAD_ABIERTOS"] = 0
        if "ALMACEN" not in df.columns:
            df["ALMACEN"] = 1
        if "FECHA_INGRESO" not in df.columns:
            df["FECHA_INGRESO"] = ""
            
        # Limpiar filas donde el producto esté vacío o sea nulo
        df = df.dropna(subset=["PRODUCTO"])
        df = df[df["PRODUCTO"].astype(str).str.strip() != ""]
        
        return df
    except Exception:
        return pd.DataFrame(columns=["PRODUCTO", "CANTIDAD_TOTAL", "CANTIDAD_ABIERTOS", "ALMACEN", "FECHA_INGRESO"])

def cargar_historial_dataframe():
    try:
        df = conn.read(worksheet="Historial", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=["PRODUCTO", "TIPO", "CANTIDAD", "FECHA", "DESCRIPCION"])
        df.columns = df.columns.astype(str).str.strip().str.upper()
        return df
    except Exception:
        return pd.DataFrame(columns=["PRODUCTO", "TIPO", "CANTIDAD", "FECHA", "DESCRIPCION"])

def limpiar_entero(valor):
    try:
        return int(float(valor))
    except (ValueError, TypeError):
        return 0

def limpiar_texto_pdf(texto):
    return str(texto).encode('latin-1', 'replace').decode('latin-1')

def registrar_en_historial(producto, tipo, cantidad, fecha, descripcion=""):
    try:
        df_historial = conn.read(worksheet="Historial", ttl=0)
        if df_historial is None or df_historial.empty:
            df_historial = pd.DataFrame(columns=["PRODUCTO", "TIPO", "CANTIDAD", "FECHA", "DESCRIPCION"])
    except Exception:
        df_historial = pd.DataFrame(columns=["PRODUCTO", "TIPO", "CANTIDAD", "FECHA", "DESCRIPCION"])
    
    nuevo_registro = pd.DataFrame([{
        "PRODUCTO": producto,
        "TIPO": tipo,
        "CANTIDAD": limpiar_entero(cantidad),
        "FECHA": fecha,
        "DESCRIPCION": descripcion
    }])
    
    df_historial_actualizado = pd.concat([df_historial, nuevo_registro], ignore_index=True)
    conn.update(worksheet="Historial", data=df_historial_actualizado.astype(str))

def registrar_en_hoja_long(usuario, accion, producto, cantidad, fecha):
    try:
        df_long = conn.read(worksheet="long", ttl=0)
        if df_long is None or df_long.empty:
            df_long = pd.DataFrame(columns=["USUARIO", "ACCION", "PRODUCTO", "CANTIDAD", "FECHA"])
    except Exception:
        df_long = pd.DataFrame(columns=["USUARIO", "ACCION", "PRODUCTO", "CANTIDAD", "FECHA"])
    
    nuevo_registro = pd.DataFrame([{
        "USUARIO": usuario,
        "ACCION": accion,
        "PRODUCTO": producto,
        "CANTIDAD": limpiar_entero(cantidad),
        "FECHA": fecha
    }])
    
    df_long_actualizado = pd.concat([df_long, nuevo_registro], ignore_index=True)
    conn.update(worksheet="long", data=df_long_actualizado.astype(str))

# ---------REGISTRO DE NUEVO PRODUCTO----------- 
def registrar_producto(nombre, cantidad_total, cantidad_abiertos, fecha, almacen): 
    df_productos = cargar_inventario_dataframe()
    nombre_mayus = nombre.strip().upper()
    
    if not df_productos.empty and "PRODUCTO" in df_productos.columns: 
        if nombre_mayus in df_productos["PRODUCTO"].astype(str).str.strip().str.upper().values: 
            st.warning("El producto ya existe en el inventario.") 
            return False
    
    cant_total_limpia = limpiar_entero(cantidad_total)
    cant_abiertos_limpia = limpiar_entero(cantidad_abiertos)

    nuevo_prod_df = pd.DataFrame([{
        "PRODUCTO": nombre_mayus,
        "CANTIDAD_TOTAL": cant_total_limpia,
        "CANTIDAD_ABIERTOS": cant_abiertos_limpia,
        "ALMACEN": almacen,
        "FECHA_INGRESO": fecha
    }])
    
    df_actualizado = pd.concat([df_productos, nuevo_prod_df], ignore_index=True)
    conn.update(worksheet="Productos", data=df_actualizado.astype(str))
    
    registrar_en_historial(nombre_mayus, "Entrada (Inicial)", cant_total_limpia, fecha, f"Inicial - Abiertos: {cant_abiertos_limpia}")
    usuario_actual = st.session_state.get("usuario", "sistema")
    registrar_en_hoja_long(usuario_actual, "Entrada (Inicial)", nombre_mayus, cant_total_limpia, fecha)
    
    return True

# ----------MOVIMIENTO DE STOCK---------- 
def registrar_movimiento(nombre, tipo_movimiento, estado, cantidad, abiertos_afectados=0, descripcion=""): 
    df_productos = cargar_inventario_dataframe()
    
    if df_productos.empty or nombre not in df_productos["PRODUCTO"].values: 
        st.warning("Producto no encontrado.") 
        return 
    
    idx = df_productos[df_productos["PRODUCTO"] == nombre].index[0]
    cant_total_actual = limpiar_entero(df_productos.loc[idx, "CANTIDAD_TOTAL"])
    cant_abiertos_actual = limpiar_entero(df_productos.loc[idx, "CANTIDAD_ABIERTOS"])
    cant_mov = limpiar_entero(cantidad)
    abiertos_mov = limpiar_entero(abiertos_afectados)
        
    if tipo_movimiento == "Salida":
        if cant_mov > cant_total_actual or abiertos_mov > cant_abiertos_actual: 
            st.warning("No hay suficiente stock total o abiertos para realizar la salida.") 
            return 
        nueva_total = cant_total_actual - cant_mov
        nuevo_abiertos = cant_abiertos_actual - abiertos_mov
    else: 
        nueva_total = cant_total_actual + cant_mov
        nuevo_abiertos = cant_abiertos_actual + abiertos_mov
        
    df_productos.loc[idx, "CANTIDAD_TOTAL"] = nueva_total
    df_productos.loc[idx, "CANTIDAD_ABIERTOS"] = nuevo_abiertos
    conn.update(worksheet="Productos", data=df_productos.astype(str))
    
    fecha_hoy = datetime.now().strftime('%Y-%m-%d')
    tipo_completo = f"{tipo_movimiento} - {estado}"
    
    registrar_en_historial(nombre, tipo_completo, cant_mov, fecha_hoy, f"{descripcion} (Abiertos: {abiertos_mov})")
    usuario_actual = st.session_state.get("usuario", "sistema")
    registrar_en_hoja_long(usuario_actual, tipo_completo, nombre, cant_mov, fecha_hoy)
    
    st.success(f"Movimiento de {tipo_completo.lower()} registrado con éxito.") 

# --------EXPORTAR REPORTE GENERAL A PDF-------- 
def exportar_pdf(): 
    df_productos = cargar_inventario_dataframe()
    pdf = FPDF() 
    pdf.add_page() 
    
    pdf.set_font("Arial", 'B', 16) 
    pdf.cell(0, 10, "Reporte de Inventario", ln=True, align='C') 
    pdf.ln(5) 
    
    w_prod, w_tot, w_ab, w_alm, w_fec = 65, 25, 25, 25, 50
    
    pdf.set_font("Arial", 'B', 9) 
    pdf.cell(w_prod, 8, "PRODUCTO", 1, 0, 'C') 
    pdf.cell(w_tot, 8, "TOTAL", 1, 0, 'C') 
    pdf.cell(w_ab, 8, "ABIERTOS", 1, 0, 'C') 
    pdf.cell(w_alm, 8, "ALMACEN", 1, 0, 'C') 
    pdf.cell(w_fec, 8, "FECHA INGRESO", 1, 1, 'C') 
    
    for _, row in df_productos.iterrows(): 
        prod_nombre = limpiar_texto_pdf(row["PRODUCTO"])
        tot = str(limpiar_entero(row["CANTIDAD_TOTAL"]))
        ab = str(limpiar_entero(row["CANTIDAD_ABIERTOS"]))
        almacen = str(row["ALMACEN"])
        fecha_ing = str(row.get("FECHA_INGRESO", "-"))
        
        pdf.set_font("Arial", '', 9)
        pdf.cell(w_prod, 8, prod_nombre, 1, 0, 'L') 
        pdf.cell(w_tot, 8, tot, 1, 0, 'C') 
        pdf.cell(w_ab, 8, ab, 1, 0, 'C') 
        pdf.cell(w_alm, 8, almacen, 1, 0, 'C') 
        pdf.cell(w_fec, 8, fecha_ing, 1, 1, 'C') 
        
    return bytes(pdf.output(dest='S'))

# --------EXPORTAR REPORTE DE PEDIDOS A PDF-------- 
def exportar_pdf_pedidos(): 
    df_productos = cargar_inventario_dataframe() 
    pdf = FPDF() 
    pdf.add_page() 
    
    pdf.set_font("Arial", 'B', 16) 
    pdf.cell(0, 10, "Reporte de Productos por Agotarse", ln=True, align='C') 
    pdf.ln(5) 
    
    w_prod, w_tot, w_ab, w_alm = 90, 30, 30, 40
    
    pdf.set_font("Arial", 'B', 10) 
    pdf.cell(w_prod, 8, "PRODUCTO", 1, 0, 'C') 
    pdf.cell(w_tot, 8, "TOTAL", 1, 0, 'C') 
    pdf.cell(w_ab, 8, "ABIERTOS", 1, 0, 'C') 
    pdf.cell(w_alm, 8, "ALMACEN", 1, 1, 'C') 
    
    for _, row in df_productos.iterrows(): 
        tot = limpiar_entero(row["CANTIDAD_TOTAL"])
        if tot <= 1: 
            prod_nombre = limpiar_texto_pdf(row["PRODUCTO"])
            pdf.set_font("Arial", '', 9)
            pdf.cell(w_prod, 8, prod_nombre, 1, 0, 'L') 
            pdf.cell(w_tot, 8, str(tot), 1, 0, 'C') 
            pdf.cell(w_ab, 8, str(limpiar_entero(row["CANTIDAD_ABIERTOS"])), 1, 0, 'C') 
            pdf.cell(w_alm, 8, str(row["ALMACEN"]), 1, 1, 'C') 
            
    return bytes(pdf.output(dest='S'))

# --------EXPORTAR A EXCEL-------- 
def exportar_excel_general(df, titulo_pestana="Inventario"):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=titulo_pestana)
        workbook = writer.book
        worksheet = writer.sheets[titulo_pestana]
        
        from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
        header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
        header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
        centered_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        left_alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        
        thin_border = Border(
            left=Side(style='thin', color='D9D9D9'), right=Side(style='thin', color='D9D9D9'),
            top=Side(style='thin', color='D9D9D9'), bottom=Side(style='thin', color='D9D9D9')
        )

        for col_idx, col_name in enumerate(df.columns, 1):
            cell_letter = worksheet.cell(row=1, column=col_idx).coordinate[0]
            header_cell = worksheet[f"{cell_letter}1"]
            header_cell.fill = header_fill
            header_cell.font = header_font
            header_cell.alignment = centered_alignment
            
            max_len = len(str(col_name))
            for row_idx in range(2, len(df) + 2):
                cell = worksheet[f"{cell_letter}{row_idx}"]
                cell.border = thin_border
                cell.font = Font(name="Arial", size=10)
                val_str = str(cell.value or '')
                if len(val_str) > max_len:
                    max_len = len(val_str)
                
                col_upper = str(col_name).upper()
                if any(k in col_upper for k in ["CANTIDAD", "TOTAL", "ABIERTOS", "ALMACEN", "FECHA", "TIPO"]):
                    cell.alignment = centered_alignment
                else:
                    cell.alignment = left_alignment
            worksheet.column_dimensions[cell_letter].width = min(max(max_len + 5, 12), 50)

    output.seek(0)
    return output.getvalue()

# --------INTERFAZ STREAMLIT---------- 
st.title("Control de Inventario GCM") 

menu = st.sidebar.selectbox(
    "Selecciona una opción", 
    ["Registrar Producto", "Registrar Movimiento", "Ver Inventario", "Historial de Movimientos", "Solicitar Pedidos"]
)

if st.sidebar.button("🔄 Actualizar datos de Google Sheets"):
    st.cache_data.clear()
    st.rerun()

# --------REGISTRAR PRODUCTO--------
if menu == "Registrar Producto": 
    st.subheader("Registrar Nuevo Producto") 

    if "nombre" not in st.session_state: st.session_state.nombre = ""
    if "cantidad_total" not in st.session_state: st.session_state.cantidad_total = 0
    if "cantidad_abiertos" not in st.session_state: st.session_state.cantidad_abiertos = 0
    if "almacen" not in st.session_state: st.session_state.almacen = 1
    if "fecha_ingreso" not in st.session_state: st.session_state.fecha_ingreso = datetime.now()

    def procesar_y_limpiar():
        nom = st.session_state.nombre
        tot = st.session_state.cantidad_total
        ab = st.session_state.cantidad_abiertos
        alm = st.session_state.almacen
        fecha_str = st.session_state.fecha_ingreso.strftime('%Y-%m-%d')
        
        if nom.strip():
            if ab > tot:
                st.error("❌ Los abiertos no pueden ser mayores a la cantidad total.")
            else:
                exito = registrar_producto(nom, tot, ab, fecha_str, alm)
                if exito:
                    st.session_state.nombre = ""
                    st.session_state.cantidad_total = 0
                    st.session_state.cantidad_abiertos = 0
                    st.session_state.almacen = 1
                    st.toast("✅ Producto registrado correctamente.")
        else:
            st.warning("Completa todos los campos.")

    st.text_input("Nombre del producto", key="nombre") 
    st.number_input("Cantidad total inicial", min_value=0, step=1, key="cantidad_total") 
    st.number_input("Cantidad abiertos inicial", min_value=0, step=1, key="cantidad_abiertos")
    st.selectbox("Almacén", [1, 2, 3, 4, 5, 6], key="almacen")
    st.date_input("Fecha de ingreso", key="fecha_ingreso")
    
    st.button("Registrar Producto", on_click=procesar_y_limpiar)

# --------MOVIMIENTOS--------
elif menu == "Registrar Movimiento": 
    st.subheader("Registrar Movimiento de Stock") 
    df_productos = cargar_inventario_dataframe() 
    
    if df_productos.empty: 
        st.info("No hay productos registrados en Google Sheets o la tabla está vacía.") 
    else: 
        productos = sorted(df_productos["PRODUCTO"].astype(str).tolist()) 
        nombre = st.selectbox("Producto", productos) 
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            tipo_mov = st.radio("Tipo", ["Entrada", "Salida"], horizontal=True)
        with col_m2:
            estado = st.radio("Estado", ["Abierto", "Cerrado"], horizontal=True)
            
        cantidad = st.number_input("Cantidad total a mover", min_value=1, step=1) 
        abiertos_afectados = st.number_input("¿Cuántos de estos son/afectan a abiertos?", min_value=0, max_value=int(cantidad), step=1)
        
        descripcion = st.text_input("Descripción (Opcional)", placeholder="Escribe un detalle o motivo opcional...")
        
        if st.button("Registrar Movimiento"): 
            registrar_movimiento(nombre, tipo_mov, estado, cantidad, abiertos_afectados, descripcion)
            st.rerun()

# --------VER INVENTARIO--------
elif menu == "Ver Inventario": 
    st.subheader("Reporte General de Inventario") 
    st.caption("Puedes corregir nombre, cantidades, almacén y fecha de ingreso.")

    df_productos = cargar_inventario_dataframe()
    
    if df_productos.empty: 
        st.info("No hay productos registrados.") 
    else: 
        lista = [] 
        for _, row in df_productos.iterrows(): 
            nombre = str(row["PRODUCTO"])
            fecha_ing = str(row.get("FECHA_INGRESO", "-"))
            
            lista.append({ 
                "Producto Original": nombre,
                "PRODUCTO": nombre, 
                "CANTIDAD TOTAL": limpiar_entero(row["CANTIDAD_TOTAL"]), 
                "CANTIDAD ABIERTOS": limpiar_entero(row["CANTIDAD_ABIERTOS"]), 
                "ALMACÉN": limpiar_entero(row["ALMACEN"]),
                "FECHA INGRESO": fecha_ing 
            }) 
        
        tabla = st.data_editor(
            lista,
            column_config={
                "Producto Original": None,
                "PRODUCTO": st.column_config.TextColumn(),
                "CANTIDAD TOTAL": st.column_config.NumberColumn(alignment="center", format="%d"),
                "CANTIDAD ABIERTOS": st.column_config.NumberColumn(alignment="center", format="%d"),
                "ALMACÉN": st.column_config.NumberColumn(alignment="center", min_value=1, max_value=6, step=1, format="%d"),
                "FECHA INGRESO": st.column_config.TextColumn(alignment="center")
            },
            hide_index=True,
            use_container_width=True
        )

        if tabla != lista:
            nombres = set()
            error = False

            for fila in tabla:
                nuevo_nombre = fila["PRODUCTO"].strip().upper()
                if nuevo_nombre in nombres:
                    st.error(f"❌ El producto '{nuevo_nombre}' está duplicado.")
                    error = True
                    break
                if fila["CANTIDAD ABIERTOS"] > fila["CANTIDAD TOTAL"]:
                    st.error(f"❌ Los abiertos de '{nuevo_nombre}' no pueden superar al total.")
                    error = True
                    break
                nombres.add(nuevo_nombre)

            if not error:
                nuevos_productos = []
                for fila in tabla:
                    nuevo_nombre = fila["PRODUCTO"].strip().upper()
                    nueva_total = limpiar_entero(fila["CANTIDAD TOTAL"])
                    nuevo_abiertos = limpiar_entero(fila["CANTIDAD ABIERTOS"])
                    nueva_fecha_ing = fila["FECHA INGRESO"]

                    nuevos_productos.append({
                        "PRODUCTO": nuevo_nombre,
                        "CANTIDAD_TOTAL": nueva_total,
                        "CANTIDAD_ABIERTOS": nuevo_abiertos,
                        "ALMACEN": fila["ALMACÉN"],
                        "FECHA_INGRESO": nueva_fecha_ing
                    })

                df_nuevos_prod = pd.DataFrame(nuevos_productos)
                conn.update(worksheet="Productos", data=df_nuevos_prod.astype(str))

                st.success("✅ Cambios guardados correctamente en Google Sheets.")
                st.rerun()

        col_pdf, col_xlsx = st.columns(2)
        with col_pdf:
            st.download_button("📥 Descargar Inventario PDF", exportar_pdf(), "reporte_inventario.pdf", mime="application/pdf")
        with col_xlsx:
            df_excel_inv = pd.DataFrame(lista).drop(columns=["Producto Original"])
            st.download_button("📊 Descargar Inventario Excel", exportar_excel_general(df_excel_inv, "Inventario"), "reporte_inventario.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# --------HISTORIAL--------
elif menu == "Historial de Movimientos":
    st.subheader("Historial de Movimientos")
    df_historial = cargar_historial_dataframe()

    if df_historial.empty:
        st.info("No hay movimientos registrados.")
    else:
        st.dataframe(
            df_historial,
            column_config={
                "CANTIDAD": st.column_config.NumberColumn(alignment="center", format="%d"),
                "FECHA": st.column_config.TextColumn(alignment="center"),
                "DESCRIPCION": st.column_config.TextColumn(width="large")
            },
            hide_index=True,
            use_container_width=True
        )
        st.download_button("📊 Descargar Historial Excel", exportar_excel_general(df_historial, "Historial"), "historial_movimientos.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# --------PEDIDOS--------
elif menu == "Solicitar Pedidos":
    st.subheader("Productos por Agotarse (Stock Total en 0 o 1)")
    df_productos = cargar_inventario_dataframe()
    bajos = []

    if not df_productos.empty:
        for _, row in df_productos.iterrows():
            tot = limpiar_entero(row["CANTIDAD_TOTAL"])
            if tot <= 1:
                bajos.append({
                    "PRODUCTO": row["PRODUCTO"],
                    "CANTIDAD_TOTAL": tot,
                    "CANTIDAD_ABIERTOS": limpiar_entero(row["CANTIDAD_ABIERTOS"]),
                    "ALMACÉN": limpiar_entero(row["ALMACEN"])
                })

    if not bajos:
        st.success("✅ Todo bien de stock")
    else:
        st.error(f"⚠️ {len(bajos)} productos requieren pedido")
        df_bajos = pd.DataFrame(bajos)
        
        st.dataframe(
            df_bajos,
            column_config={
                "PRODUCTO": st.column_config.TextColumn(),
                "CANTIDAD_TOTAL": st.column_config.NumberColumn(alignment="center", format="%d"),
                "CANTIDAD_ABIERTOS": st.column_config.NumberColumn(alignment="center", format="%d"),
                "ALMACÉN": st.column_config.NumberColumn(alignment="center", format="%d")
            },
            hide_index=True,
            use_container_width=True
        )

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.download_button("📥 Descargar Pedidos PDF", exportar_pdf_pedidos(), "reporte_pedidos.pdf", mime="application/pdf")
        with col_p2:
            st.download_button("📊 Descargar Pedidos Excel", exportar_excel_general(df_bajos, "Pedidos"), "reporte_pedidos.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")