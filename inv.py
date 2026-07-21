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
def registrar_producto(nombre, cantidad, fecha, almacen): 
    inventario = cargar_inventario() 
    nombre = nombre.strip().upper()
    
    if nombre in inventario: 
        st.warning("El producto ya existe.") 
        return 
    
    inventario[nombre] = { 
        "cantidad": limpiar_entero(cantidad),
        "almacen": almacen,
        "fecha_ingreso": fecha, 
        "movimientos": [{ 
            "tipo": "ingreso inicial", 
            "cantidad": limpiar_entero(cantidad), 
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
    
    actual = limpiar_entero(inventario[nombre]["cantidad"])
    cantidad = limpiar_entero(cantidad)
        
    if tipo == "Salida" and cantidad > actual: 
        st.warning("Stock insuficiente.") 
        return 
        
    if tipo == "Entrada": 
        inventario[nombre]["cantidad"] = actual + cantidad
    else: 
        inventario[nombre]["cantidad"] = actual - cantidad
        
    inventario[nombre]["movimientos"].append({ 
        "tipo": tipo, 
        "cantidad": cantidad, 
        "fecha": datetime.now().strftime('%Y-%m-%d') 
    }) 
    
    guardar_inventario(inventario) 
    st.success("Movimiento registrado.") 

# --------PDF-------- 
def exportar_pdf(): 
    inventario = cargar_inventario() 
    pdf = FPDF() 
    pdf.add_page() 
    
    pdf.set_font("Arial", 'B', 16) 
    pdf.cell(0, 10, "Inventario", ln=True, align='C') 
    pdf.ln(10) 
    
    for nombre, datos in inventario.items(): 
        pdf.set_font("Arial", '', 10) 
        pdf.cell(0, 10, f"{nombre} - Cantidad: {datos['cantidad']} - Almacén: {datos['almacen']}", ln=True) 
        
    return bytes(pdf.output(dest='S'))

# --------INTERFAZ---------- 
st.title("Inventario")

menu = st.sidebar.selectbox("Menú", ["Registrar Producto", "Movimiento", "Ver Inventario"])

# --------REGISTRAR PRODUCTO--------
if menu == "Registrar Producto":

    def limpiar_form():
        st.session_state.nombre = ""
        st.session_state.cantidad = 0
        st.session_state.almacen = 1

    def registrar_y_limpiar():
        if st.session_state.nombre:
            registrar_producto(
                st.session_state.nombre,
                st.session_state.cantidad,
                datetime.now().strftime('%Y-%m-%d'),
                st.session_state.almacen
            )
            limpiar_form()
        else:
            st.warning("Completa los campos")

    st.text_input("Nombre", key="nombre")
    st.number_input("Cantidad", min_value=0, key="cantidad")
    st.selectbox("Almacén", [1,2,3,4,5,6], key="almacen")

    st.button("Registrar", on_click=registrar_y_limpiar)

# --------MOVIMIENTO--------
elif menu == "Movimiento":
    inventario = cargar_inventario()
    productos = list(inventario.keys())

    if productos:
        nombre = st.selectbox("Producto", productos)
        tipo = st.radio("Tipo", ["Entrada", "Salida"])
        cantidad = st.number_input("Cantidad", min_value=1)

        if st.button("Aplicar"):
            registrar_movimiento(nombre, tipo, cantidad)
    else:
        st.info("No hay productos")

# --------VER INVENTARIO--------
elif menu == "Ver Inventario":
    inventario = cargar_inventario()

    if inventario:
        st.json(inventario)
        st.download_button("Descargar PDF", exportar_pdf(), "inventario.pdf")
    else:
        st.info("Vacío")