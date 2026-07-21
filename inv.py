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
    except:
        return 0

# ---------REGISTRO DE NUEVO PRODUCTO----------- 
def registrar_producto(nombre, cantidad, almacen, fecha): 
    inventario = cargar_inventario() 
    nombre = nombre.strip().upper()

    if nombre in inventario: 
        st.warning("El producto ya existe.") 
        return 

    inventario[nombre] = { 
        "cantidad": limpiar_entero(cantidad),
        "almacen": limpiar_entero(almacen),
        "fecha_ingreso": fecha,
        "movimientos": [{
            "tipo": "ingreso inicial",
            "cantidad": limpiar_entero(cantidad),
            "fecha": fecha
        }]
    }

    guardar_inventario(inventario)
    st.success("Producto registrado")

# ----------MOVIMIENTO----------
def registrar_movimiento(nombre, tipo, cantidad):
    inventario = cargar_inventario()

    if nombre not in inventario:
        st.warning("Producto no encontrado")
        return

    cantidad_actual = limpiar_entero(inventario[nombre]["cantidad"])
    cantidad = limpiar_entero(cantidad)

    if tipo == "Salida" and cantidad > cantidad_actual:
        st.warning("No hay suficiente stock")
        return

    if tipo == "Entrada":
        inventario[nombre]["cantidad"] += cantidad
    else:
        inventario[nombre]["cantidad"] -= cantidad

    inventario[nombre]["movimientos"].append({
        "tipo": tipo,
        "cantidad": cantidad,
        "fecha": datetime.now().strftime('%Y-%m-%d')
    })

    guardar_inventario(inventario)
    st.success("Movimiento registrado")

# --------PDF--------
def exportar_pdf():
    inventario = cargar_inventario()
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "REPORTE DE INVENTARIO", ln=True, align='C')
    pdf.ln(10)

    pdf.set_font("Arial", 'B', 10)
    pdf.cell(50, 10, "PRODUCTO", 1)
    pdf.cell(30, 10, "CANTIDAD", 1)
    pdf.cell(30, 10, "ALMACEN", 1)
    pdf.cell(60, 10, "ULTIMO MOVIMIENTO", 1)
    pdf.ln()

    pdf.set_font("Arial", '', 10)
    for nombre, datos in inventario.items():
        ult = datos["movimientos"][-1]["fecha"] if datos["movimientos"] else "-"
        pdf.cell(50, 10, nombre, 1)
        pdf.cell(30, 10, str(datos["cantidad"]), 1)
        pdf.cell(30, 10, str(datos.get("almacen", "")), 1)
        pdf.cell(60, 10, ult, 1)
        pdf.ln()

    return bytes(pdf.output(dest='S'))

# --------INTERFAZ--------
st.set_page_config(page_title="Inventario", layout="centered")
st.title("Control de Inventario")

menu = st.sidebar.selectbox(
    "Menú",
    ["Registrar Producto", "Registrar Movimiento", "Ver Inventario"]
)

# --------REGISTRAR--------
if menu == "Registrar Producto":
    nombre = st.text_input("Producto")
    cantidad = st.number_input("Cantidad", min_value=0)
    almacen = st.selectbox("Almacen", [1, 2, 3, 4])
    fecha = st.date_input("Fecha", value=datetime.now()).strftime('%Y-%m-%d')

    if st.button("Guardar"):
        registrar_producto(nombre, cantidad, almacen, fecha)

# --------MOVIMIENTO--------
elif menu == "Registrar Movimiento":
    inventario = cargar_inventario()
    productos = list(inventario.keys())

    if productos:
        nombre = st.selectbox("Producto", productos)
        tipo = st.radio("Tipo", ["Entrada", "Salida"])
        cantidad = st.number_input("Cantidad", min_value=1)

        if st.button("Registrar"):
            registrar_movimiento(nombre, tipo, cantidad)
    else:
        st.info("No hay productos")

# --------VER INVENTARIO--------
elif menu == "Ver Inventario":
    inventario = cargar_inventario()

    if not inventario:
        st.info("No hay productos")
    else:
        lista = []
        for nombre, datos in inventario.items():
            ult = datos["movimientos"][-1]["fecha"] if datos["movimientos"] else "-"
            lista.append({
                "Producto Original": nombre,
                "PRODUCTO": nombre,
                "CANTIDAD": datos["cantidad"],
                "ALMACEN": datos.get("almacen", ""),
                "ULTIMO MOVIMIENTO": ult
            })

        tabla = st.data_editor(
            lista,
            num_rows="dynamic",
            column_config={
                "Producto Original": None,
                "CANTIDAD": st.column_config.NumberColumn(disabled=True),
                "ULTIMO MOVIMIENTO": st.column_config.TextColumn(disabled=True)
            },
            hide_index=True,
            use_container_width=True
        )

        if st.button("Guardar Cambios"):
            nuevo = {}

            for fila in tabla:
                nombre = fila["PRODUCTO"].strip().upper()
                original = fila["Producto Original"]

                if nombre == "":
                    continue  # elimina fila vacía

                nuevo[nombre] = inventario.get(original, {})
                nuevo[nombre]["almacen"] = limpiar_entero(fila["ALMACEN"])

            guardar_inventario(nuevo)
            st.success("Cambios guardados")
            st.rerun()

        st.download_button("Descargar PDF", exportar_pdf(), "inventario.pdf")