import streamlit as st 
import json 
import os 
from datetime import datetime 
from fpdf import FPDF 

# -------CONSTANTES----- 
ARCHIVO = "inventario.json" 

# -------Funciones de Persistencia--------- 
def cargar_inventario(): 
    if not os.path.exists(ARCHIVO): 
        return {} 
    try: 
        with open(ARCHIVO, 'r', encoding='utf-8') as f: 
            return json.load(f) 
    except json.JSONDecodeError: 
        return {} 

def guardar_inventario(data): 
    with open(ARCHIVO, 'w', encoding='utf-8') as f: 
        json.dump(data, f, indent=4) 

def limpiar_entero(valor):
    try:
        return int(valor)
    except (ValueError, TypeError):
        return 0

# ---------REGISTRO DE NUEVO PRODUCTO----------- 
def registrar_producto(nombre, cantidad, fecha, almacen): 
    inventario = cargar_inventario() 
    nombre_mayus = nombre.strip().upper()
    
    if nombre_mayus in inventario: 
        st.warning("El producto ya existe en el inventario.") 
        return 
    
    cant_limpia = limpiar_entero(cantidad)

    inventario[nombre_mayus] = { 
        "cantidad": cant_limpia,
        "almacen": almacen,
        "fecha_ingreso": fecha, 
        "movimientos": [{ 
            "tipo": "ingreso inicial", 
            "cantidad": cant_limpia, 
            "fecha": fecha 
        }] 
    } 
    guardar_inventario(inventario) 
    st.success("Producto registrado correctamente.") 

# ----------MOVIMIENTO DE STOCK---------- 
def registrar_movimiento(nombre, tipo, cantidad): 
    inventario = cargar_inventario() 
    
    if nombre not in inventario: 
        st.warning("Producto no encontrado") 
        return 
    
    cantidad_actual = limpiar_entero(inventario[nombre].get("cantidad", 0))
    cantidad_mov = limpiar_entero(cantidad)
        
    if tipo == "Salida" and cantidad_mov > cantidad_actual: 
        st.warning("No hay suficiente stock para realizar la salida.") 
        return 
        
    if tipo == "Entrada": 
        inventario[nombre]["cantidad"] = cantidad_actual + cantidad_mov
    elif tipo == "Salida": 
        inventario[nombre]["cantidad"] = cantidad_actual - cantidad_mov
        
    inventario[nombre]["movimientos"].append({ 
        "tipo": tipo, 
        "cantidad": cantidad_mov, 
        "fecha": datetime.now().strftime('%Y-%m-%d') 
    }) 
    
    guardar_inventario(inventario) 
    st.success(f"Movimiento de {tipo.lower()} registrado.") 

# --------EXPORTAR REPORTE GENERAL A PDF-------- 
def exportar_pdf(): 
    inventario = cargar_inventario() 
    pdf = FPDF() 
    pdf.add_page() 
    
    pdf.set_font("Arial", 'B', 16) 
    pdf.cell(0, 10, "Reporte de Inventario", ln=True, align='C') 
    pdf.ln(10) 
    
    pdf.set_font("Arial", 'B', 10) 
    pdf.cell(50, 10, "PRODUCTO", 1) 
    pdf.cell(30, 10, "CANTIDAD", 1) 
    pdf.cell(30, 10, "ALMACEN", 1) 
    pdf.cell(50, 10, "ULTIMO MOVIMIENTO", 1) 
    pdf.ln() 
    
    pdf.set_font("Arial", '', 10) 
    for nombre, datos in inventario.items(): 
        movimientos = datos.get("movimientos", [])
        ult_mov = movimientos[-1]["fecha"] if movimientos else "-"
        cant = limpiar_entero(datos.get("cantidad", 0))
        almacen = datos.get("almacen", "-")
        
        pdf.cell(50, 10, nombre, 1) 
        pdf.cell(30, 10, str(cant), 1) 
        pdf.cell(30, 10, str(almacen), 1) 
        pdf.cell(50, 10, str(ult_mov), 1) 
        pdf.ln() 
        
    return bytes(pdf.output(dest='S'))

# --------EXPORTAR REPORTE DE PEDIDOS-------- 
def exportar_pdf_pedidos(): 
    inventario = cargar_inventario() 
    pdf = FPDF() 
    pdf.add_page() 
    
    pdf.set_font("Arial", 'B', 16) 
    pdf.cell(0, 10, "Reporte de Productos por Agotarse", ln=True, align='C') 
    pdf.ln(10) 
    
    pdf.set_font("Arial", 'B', 10) 
    pdf.cell(70, 10, "PRODUCTO", 1) 
    pdf.cell(30, 10, "CANTIDAD", 1) 
    pdf.cell(30, 10, "ALMACEN", 1) 
    pdf.ln() 
    
    pdf.set_font("Arial", '', 10) 
    for nombre, datos in inventario.items(): 
        cant = limpiar_entero(datos.get("cantidad", 0))
        almacen = datos.get("almacen", "-")
        if cant <= 1: 
            pdf.cell(70, 10, nombre, 1) 
            pdf.cell(30, 10, str(cant), 1) 
            pdf.cell(30, 10, str(almacen), 1) 
            pdf.ln() 
            
    return bytes(pdf.output(dest='S'))

# --------INTERFAZ STREAMLIT---------- 
st.set_page_config(page_title="Control de Inventario GCM", layout="centered") 
st.title("Control de Inventario GCM") 

menu = st.sidebar.selectbox(
    "Selecciona una opción", 
    ["Registrar Producto", "Registrar Movimiento", "Ver Inventario", "Historial de Movimientos", "Solicitar Pedidos"]
)

# --------REGISTRAR PRODUCTO--------
if menu == "Registrar Producto": 
    st.subheader("Registrar Nuevo Producto") 
    nombre = st.text_input("Nombre del producto") 
    cantidad = st.number_input("Cantidad inicial", min_value=0, step=1) 
    almacen = st.selectbox("Almacén", [1, 2, 3, 4])
    fecha = st.date_input("Fecha de ingreso", value=datetime.now()).strftime('%Y-%m-%d') 
    
    if st.button("Registrar Producto"): 
        if nombre: 
            registrar_producto(nombre, cantidad, fecha, almacen) 
        else: 
            st.warning("Completa todos los campos.") 

# --------MOVIMIENTOS--------
elif menu == "Registrar Movimiento": 
    st.subheader("Registrar Movimiento de Stock") 
    inventario = cargar_inventario() 
    productos = sorted(list(inventario.keys())) 
    
    if not productos: 
        st.info("No hay productos registrados.") 
    else: 
        nombre = st.selectbox("Producto", productos) 
        tipo = st.radio("Tipo", ["Entrada", "Salida"]) 
        cantidad = st.number_input("Cantidad", min_value=1) 
        
        if st.button("Registrar Movimiento"): 
            registrar_movimiento(nombre, tipo, cantidad) 

# --------VER INVENTARIO--------
elif menu == "Ver Inventario": 
    st.subheader("Reporte General de Inventario") 
    st.caption("💡 Puedes corregir el nombre y el almacén directamente.")

    inventario = cargar_inventario() 
    
    if not inventario: 
        st.info("No hay productos.") 
    else: 
        lista = [] 
        for nombre, datos in inventario.items(): 
            movimientos = datos.get("movimientos", [])
            ult = movimientos[-1]["fecha"] if movimientos else "-"
            
            lista.append({ 
                "Producto Original": nombre,
                "PRODUCTO": nombre, 
                "CANTIDAD": limpiar_entero(datos.get("cantidad", 0)), 
                "ALMACÉN": datos.get("almacen", "-"),
                "ULTIMO MOVIMIENTO": ult 
            }) 
        
        tabla = st.data_editor(
            lista,
            column_config={
                "Producto Original": None,
                "PRODUCTO": st.column_config.TextColumn(),
                "CANTIDAD": st.column_config.NumberColumn(disabled=True),
                "ALMACÉN": st.column_config.SelectboxColumn(
                    options=[1, 2, 3, 4, 5, 6],
                    required=True
                ),
                "ULTIMO MOVIMIENTO": st.column_config.TextColumn(disabled=True)
            },
            hide_index=True,
            use_container_width=True
        )

        if tabla != lista:
            nuevo = {}
            nombres = set()
            error = False

            for fila in tabla:
                nuevo_nombre = fila["PRODUCTO"].strip().upper()
                original = fila["Producto Original"]

                if nuevo_nombre in nombres or (nuevo_nombre in inventario and nuevo_nombre != original):
                    st.error(f"❌ El producto '{nuevo_nombre}' ya existe.")
                    error = True
                    break

                nombres.add(nuevo_nombre)

            if not error:
                for fila in tabla:
                    original = fila["Producto Original"]
                    nuevo_nombre = fila["PRODUCTO"].strip().upper()

                    nuevo[nuevo_nombre] = inventario[original]
                    nuevo[nuevo_nombre]["almacen"] = fila["ALMACÉN"]

                guardar_inventario(nuevo)
                st.success("✅ Cambios guardados correctamente")
                st.rerun()

        st.download_button("Descargar PDF", exportar_pdf(), "reporte_inventario.pdf")

# --------HISTORIAL--------
elif menu == "Historial de Movimientos":
    st.subheader("Historial de Movimientos")

    inventario = cargar_inventario()
    historial = []

    for nombre, datos in inventario.items():
        for mov in datos.get("movimientos", []):
            historial.append({
                "PRODUCTO": nombre,
                "TIPO": mov.get("tipo", "-"),
                "CANTIDAD": mov.get("cantidad", 0),
                "FECHA": mov.get("fecha", "-")
            })

    if not historial:
        st.info("No hay movimientos registrados.")
    else:
        st.dataframe(historial, use_container_width=True)

# --------PEDIDOS--------
elif menu == "Solicitar Pedidos":
    st.subheader("Productos por Agotarse (Stock en 0 o 1)")

    inventario = cargar_inventario()
    bajos = []

    for nombre, datos in inventario.items():
        cant = limpiar_entero(datos.get("cantidad", 0))
        almacen = datos.get("almacen", "-")
        if cant <= 1:
            bajos.append({
                "PRODUCTO": nombre,
                "CANTIDAD": cant,
                "ALMACÉN": almacen
            })

    if not bajos:
        st.success("✅ Todo bien de stock")
    else:
        st.error(f"⚠️ {len(bajos)} productos requieren pedido")
        st.table(bajos)

        st.download_button(
            "Descargar pedidos PDF",
            exportar_pdf_pedidos(),
            "reporte_pedidos.pdf"
        )