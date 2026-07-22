import streamlit as st 
import pandas as pd
from datetime import datetime 
from fpdf import FPDF 
from streamlit_gsheets import GSheetsConnection
import io

# ------- CONFIGURACIÓN DE PÁGINA ---------
st.set_page_config(
    page_title="Control de Inventario GCM", 
    layout="centered",
    initial_sidebar_state="expanded"
) 


# 🔐 USUARIOS AUTORIZADOS (EDITA AQUÍ)
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


# ------- CONFIGURACIÓN DE PÁGINA ---------
st.set_page_config(
    page_title="Control de Inventario GCM", 
    layout="centered",
    initial_sidebar_state="expanded"
) 


# -------Conexión a Google Sheets--------- 
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_inventario_dataframe(): 
    """Lee la pestaña 'Productos' de Google Sheets en tiempo real (ttl=0)."""
    try:
        df = conn.read(worksheet="Productos", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=["PRODUCTO", "CANTIDAD_ACTUAL", "ALMACEN", "FECHA_INGRESO"])
        return df
    except Exception:
        return pd.DataFrame(columns=["PRODUCTO", "CANTIDAD_ACTUAL", "ALMACEN", "FECHA_INGRESO"])

def cargar_historial_dataframe():
    """Lee la pestaña 'Historial' de Google Sheets en tiempo real (ttl=0)."""
    try:
        df = conn.read(worksheet="Historial", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=["PRODUCTO", "TIPO", "CANTIDAD", "FECHA"])
        return df
    except Exception:
        return pd.DataFrame(columns=["PRODUCTO", "TIPO", "CANTIDAD", "FECHA"])

def limpiar_entero(valor):
    try:
        return int(valor)
    except (ValueError, TypeError):
        return 0

def limpiar_texto_pdf(texto):
    """Convierte texto a latin-1 para evitar errores en FPDF con tildes/eñes."""
    return str(texto).encode('latin-1', 'replace').decode('latin-1')

# ---------REGISTRO DE NUEVO PRODUCTO----------- 
def registrar_producto(nombre, cantidad, fecha, almacen): 
    df_productos = cargar_inventario_dataframe()
    nombre_mayus = nombre.strip().upper()
    
    if not df_productos.empty and "PRODUCTO" in df_productos.columns: 
        if nombre_mayus in df_productos["PRODUCTO"].astype(str).str.strip().str.upper().values: 
            st.warning("El producto ya existe en el inventario.") 
            return False
    
    cant_limpia = limpiar_entero(cantidad)

    nuevo_prod_df = pd.DataFrame([{
        "PRODUCTO": nombre_mayus,
        "CANTIDAD_ACTUAL": cant_limpia,
        "ALMACEN": almacen,
        "FECHA_INGRESO": fecha
    }])
    
    df_actualizado = pd.concat([df_productos, nuevo_prod_df], ignore_index=True)
    
    df_historial = cargar_historial_dataframe()
    nuevo_mov_df = pd.DataFrame([{
        "PRODUCTO": nombre_mayus,
        "TIPO": "Entrada (Inicial)",
        "CANTIDAD": cant_limpia,
        "FECHA": fecha
    }])
    df_historial_actualizado = pd.concat([df_historial, nuevo_mov_df], ignore_index=True)
    
    conn.update(worksheet="Productos", data=df_actualizado.astype(str))
    conn.update(worksheet="Historial", data=df_historial_actualizado.astype(str))
    return True

# ----------MOVIMIENTO DE STOCK---------- 
def registrar_movimiento(nombre, tipo, cantidad): 
    df_productos = cargar_inventario_dataframe()
    
    if df_productos.empty or nombre not in df_productos["PRODUCTO"].values: 
        st.warning("Producto no encontrado.") 
        return 
    
    idx = df_productos[df_productos["PRODUCTO"] == nombre].index[0]
    cant_actual = limpiar_entero(df_productos.loc[idx, "CANTIDAD_ACTUAL"])
    cant_mov = limpiar_entero(cantidad)
        
    if tipo == "Salida" and cant_mov > cant_actual: 
        st.warning("No hay suficiente stock para realizar la salida.") 
        return 
        
    if tipo == "Entrada": 
        nueva_cant = cant_actual + cant_mov
    else: 
        nueva_cant = cant_actual - cant_mov
        
    df_productos.loc[idx, "CANTIDAD_ACTUAL"] = nueva_cant
    
    fecha_hoy = datetime.now().strftime('%Y-%m-%d')
    df_historial = cargar_historial_dataframe()
    nuevo_mov = pd.DataFrame([{
        "PRODUCTO": nombre,
        "TIPO": tipo,
        "CANTIDAD": cant_mov,
        "FECHA": fecha_hoy
    }])
    df_historial_actualizado = pd.concat([df_historial, nuevo_mov], ignore_index=True)
    
    conn.update(worksheet="Productos", data=df_productos.astype(str))
    conn.update(worksheet="Historial", data=df_historial_actualizado.astype(str))
    st.success(f"Movimiento de {tipo.lower()} registrado con éxito.") 

# --------EXPORTAR REPORTE GENERAL A PDF-------- 
def exportar_pdf(): 
    df_productos = cargar_inventario_dataframe()
    
    pdf = FPDF() 
    pdf.add_page() 
    
    pdf.set_font("Arial", 'B', 16) 
    pdf.cell(0, 10, "Reporte de Inventario", ln=True, align='C') 
    pdf.ln(5) 
    
    w_prod, w_cant, w_alm, w_fec = 75, 30, 30, 55
    
    pdf.set_font("Arial", 'B', 10) 
    pdf.cell(w_prod, 8, "PRODUCTO", 1, 0, 'C') 
    pdf.cell(w_cant, 8, "CANTIDAD", 1, 0, 'C') 
    pdf.cell(w_alm, 8, "ALMACEN", 1, 0, 'C') 
    pdf.cell(w_fec, 8, "FECHA INGRESO", 1, 1, 'C') 
    
    for _, row in df_productos.iterrows(): 
        prod_nombre = limpiar_texto_pdf(row["PRODUCTO"])
        cant = str(limpiar_entero(row["CANTIDAD_ACTUAL"]))
        almacen = str(row["ALMACEN"])
        fecha_ing = str(row.get("FECHA_INGRESO", "-"))
        
        pdf.set_font("Arial", '', 9)
        if pdf.get_string_width(prod_nombre) > (w_prod - 3):
            pdf.set_font("Arial", '', 7.5)
            if pdf.get_string_width(prod_nombre) > (w_prod - 3):
                pdf.set_font("Arial", '', 6.5)
        
        pdf.cell(w_prod, 8, prod_nombre, 1, 0, 'L') 
        
        pdf.set_font("Arial", '', 9)
        pdf.cell(w_cant, 8, cant, 1, 0, 'C') 
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
    
    w_prod, w_cant, w_alm = 110, 40, 40
    
    pdf.set_font("Arial", 'B', 10) 
    pdf.cell(w_prod, 8, "PRODUCTO", 1, 0, 'C') 
    pdf.cell(w_cant, 8, "CANTIDAD", 1, 0, 'C') 
    pdf.cell(w_alm, 8, "ALMACEN", 1, 1, 'C') 
    
    for _, row in df_productos.iterrows(): 
        cant = limpiar_entero(row["CANTIDAD_ACTUAL"])
        if cant <= 1: 
            prod_nombre = limpiar_texto_pdf(row["PRODUCTO"])
            
            pdf.set_font("Arial", '', 9)
            if pdf.get_string_width(prod_nombre) > (w_prod - 3):
                pdf.set_font("Arial", '', 7.5)
                if pdf.get_string_width(prod_nombre) > (w_prod - 3):
                    pdf.set_font("Arial", '', 6.5)

            pdf.cell(w_prod, 8, prod_nombre, 1, 0, 'L') 
            
            pdf.set_font("Arial", '', 9)
            pdf.cell(w_cant, 8, str(cant), 1, 0, 'C') 
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
            left=Side(style='thin', color='D9D9D9'),
            right=Side(style='thin', color='D9D9D9'),
            top=Side(style='thin', color='D9D9D9'),
            bottom=Side(style='thin', color='D9D9D9')
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
                if any(k in col_upper for k in ["CANTIDAD", "ALMACEN", "ALMACÉN", "FECHA", "TIPO"]):
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

    if "nombre" not in st.session_state:
        st.session_state.nombre = ""
    if "cantidad" not in st.session_state:
        st.session_state.cantidad = 0
    if "almacen" not in st.session_state:
        st.session_state.almacen = 1
    if "fecha_ingreso" not in st.session_state:
        st.session_state.fecha_ingreso = datetime.now()

    def procesar_y_limpiar():
        nom = st.session_state.nombre
        cant = st.session_state.cantidad
        alm = st.session_state.almacen
        fecha_str = st.session_state.fecha_ingreso.strftime('%Y-%m-%d')
        
        if nom.strip():
            exito = registrar_producto(nom, cant, fecha_str, alm)
            if exito:
                st.session_state.nombre = ""
                st.session_state.cantidad = 0
                st.session_state.almacen = 1
                st.toast("✅ Producto registrado correctamente.")
        else:
            st.warning("Completa todos los campos.")

    st.text_input("Nombre del producto", key="nombre") 
    st.number_input("Cantidad inicial", min_value=0, step=1, key="cantidad") 
    st.selectbox("Almacén", [1, 2, 3, 4, 5, 6], key="almacen")
    st.date_input("Fecha de ingreso", key="fecha_ingreso")
    
    st.button("Registrar Producto", on_click=procesar_y_limpiar)

# --------MOVIMIENTOS--------
elif menu == "Registrar Movimiento": 
    st.subheader("Registrar Movimiento de Stock") 
    df_productos = cargar_inventario_dataframe() 
    
    if df_productos.empty: 
        st.info("No hay productos registrados.") 
    else: 
        productos = sorted(df_productos["PRODUCTO"].astype(str).tolist()) 
        nombre = st.selectbox("Producto", productos) 
        tipo = st.radio("Tipo", ["Entrada", "Salida"]) 
        cantidad = st.number_input("Cantidad", min_value=1, step=1) 
        
        if st.button("Registrar Movimiento"): 
            registrar_movimiento(nombre, tipo, cantidad)
            st.rerun()

# --------VER INVENTARIO--------
elif menu == "Ver Inventario": 
    st.subheader("Reporte General de Inventario") 
    st.caption("Puedes corregir nombre, cantidad, almacén y fecha de ingreso.")

    df_productos = cargar_inventario_dataframe()
    df_historial = cargar_historial_dataframe()
    
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
                "CANTIDAD": limpiar_entero(row["CANTIDAD_ACTUAL"]), 
                "ALMACÉN": limpiar_entero(row["ALMACEN"]),
                "FECHA INGRESO": fecha_ing 
            }) 
        
        tabla = st.data_editor(
            lista,
            column_config={
                "Producto Original": None,
                "PRODUCTO": st.column_config.TextColumn(),
                "CANTIDAD": st.column_config.NumberColumn(
                    alignment="center",
                    format="%d"
                ),
                "ALMACÉN": st.column_config.NumberColumn(
                    alignment="center",
                    min_value=1,
                    max_value=6,
                    step=1,
                    format="%d"
                ),
                "FECHA INGRESO": st.column_config.TextColumn(
                    alignment="center"
                )
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
                nombres.add(nuevo_nombre)

            if not error:
                nuevos_productos = []
                fecha_hoy = datetime.now().strftime('%Y-%m-%d')

                for fila in tabla:
                    original = fila["Producto Original"]
                    nuevo_nombre = fila["PRODUCTO"].strip().upper()
                    nueva_cantidad = limpiar_entero(fila["CANTIDAD"])
                    nueva_fecha_ing = fila["FECHA INGRESO"]

                    fila_previa = df_productos[df_productos["PRODUCTO"] == original]
                    cant_anterior = limpiar_entero(fila_previa["CANTIDAD_ACTUAL"].values[0]) if not fila_previa.empty else 0

                    nuevos_productos.append({
                        "PRODUCTO": nuevo_nombre,
                        "CANTIDAD_ACTUAL": nueva_cantidad,
                        "ALMACEN": fila["ALMACÉN"],
                        "FECHA_INGRESO": nueva_fecha_ing
                    })

                    if nueva_cantidad != cant_anterior:
                        diferencia = nueva_cantidad - cant_anterior
                        tipo_mov = "Ajuste +" if diferencia > 0 else "Ajuste -"

                        df_historial = pd.concat([df_historial, pd.DataFrame([{
                            "PRODUCTO": nuevo_nombre,
                            "TIPO": tipo_mov,
                            "CANTIDAD": abs(diferencia),
                            "FECHA": fecha_hoy
                        }])], ignore_index=True)

                df_nuevos_prod = pd.DataFrame(nuevos_productos)
                conn.update(worksheet="Productos", data=df_nuevos_prod.astype(str))
                conn.update(worksheet="Historial", data=df_historial.astype(str))

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
                "CANTIDAD": st.column_config.NumberColumn(
                    alignment="center",
                    format="%d"
                ),
                "FECHA": st.column_config.TextColumn(
                    alignment="center"
                )
            },
            hide_index=True,
            use_container_width=True
        )

        st.download_button("📊 Descargar Historial Excel", exportar_excel_general(df_historial, "Historial"), "historial_movimientos.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# --------PEDIDOS--------
elif menu == "Solicitar Pedidos":
    st.subheader("Productos por Agotarse (Stock en 0 o 1)")

    df_productos = cargar_inventario_dataframe()
    bajos = []

    if not df_productos.empty:
        for _, row in df_productos.iterrows():
            cant = limpiar_entero(row["CANTIDAD_ACTUAL"])
            if cant <= 1:
                bajos.append({
                    "PRODUCTO": row["PRODUCTO"],
                    "CANTIDAD": cant,
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
                "CANTIDAD": st.column_config.NumberColumn(
                    alignment="center",
                    format="%d"
                ),
                "ALMACÉN": st.column_config.NumberColumn(
                    alignment="center",
                    format="%d"
                )
            },
            hide_index=True,
            use_container_width=True
        )

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.download_button(
                "📥 Descargar Pedidos PDF",
                exportar_pdf_pedidos(),
                "reporte_pedidos.pdf",
                mime="application/pdf"
            )
        with col_p2:
            st.download_button(
                "📊 Descargar Pedidos Excel",
                exportar_excel_general(df_bajos, "Pedidos"),
                "reporte_pedidos.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )