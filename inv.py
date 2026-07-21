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

# ---------REGISTRO DE NUEVO PRODUCTO----------- 
def registrar_producto(nombre, cantidad, fecha): 
    inventario = cargar_inventario() 
    if nombre in inventario: 
        st.warning("El producto ya existe en el inventario.") 
        return 
    
    inventario[nombre] = { 
        "cantidad": cantidad, 
        "fecha_ingreso": fecha, 
        "movimientos": [{ 
            "tipo": "ingreso inicial", 
            "cantidad": cantidad, 
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
        
    if tipo == "Salida" and cantidad > inventario[nombre]["cantidad"]: 
        st.warning("No hay suficiente stock para realizar la salida.") 
        return 
        
    if tipo == "Entrada": 
        inventario[nombre]["cantidad"] += cantidad 
    elif tipo == "Salida": 
        inventario[nombre]["cantidad"] -= cantidad 
        
    inventario[nombre]["movimientos"].append({ 
        "tipo": tipo, 
        "cantidad": cantidad, 
        "fecha": datetime.now().strftime('%Y-%m-%d %H:%M:%S') 
    }) 
    
    guardar_inventario(inventario) 
    st.success(f"Movimiento de {tipo.lower()} registrado.") 

# --------EXPORTAR REPORTE A PDF-------- 
def exportar_pdf(): 
    inventario = cargar_inventario() 
    pdf = FPDF() 
    pdf.add_page() 
    
    # Configuración de fuente (Corregido a set_font)
    pdf.set_font("Arial", 'B', 16) 
    pdf.cell(0, 10, "Reporte de inventario", ln=True, align='C') 
    pdf.ln(10) 
    
    pdf.set_font("Arial", 'B', 10) 
    pdf.cell(60, 10, "Producto", 1) 
    pdf.cell(30, 10, "Cantidad", 1) 
    pdf.cell(80, 10, "Ultimo movimiento", 1) 
    pdf.ln() 
    
    pdf.set_font("Arial", '', 10) 
    for nombre, datos in inventario.items(): 
        movimientos = datos.get("movimientos", [])
        ult_mov = movimientos[-1]["fecha"] if movimientos else "-"
        
        pdf.cell(60, 10, nombre, 1) 
        pdf.cell(30, 10, str(datos["cantidad"]), 1) 
        pdf.cell(80, 10, str(ult_mov), 1) 
        pdf.ln() 
        
    nombre_archivo = "reporte_inventario.pdf" 
    pdf.output(nombre_archivo) 
    return nombre_archivo 

# --------INTERFAZ STREAMLIT---------- 
st.set_page_config(page_title="Control de Inventario", layout="centered") 
st.title("Control de Inventario") 

menu = st.sidebar.selectbox("Selecciona una opción", ["Registrar Producto", "Registrar Movimiento", "Ver Inventario"]) 

# -------REGISTRAR PRODUCTO--------- 
if menu == "Registrar Producto": 
    st.subheader("Registrar Nuevo Producto") 
    nombre = st.text_input("Nombre del producto") 
    cantidad = st.number_input("Cantidad inicial", min_value=0, step=1) 
    fecha = st.date_input("Fecha de ingreso", value=datetime.now()).strftime('%Y-%m-%d') 
    
    if st.button("Registrar Producto"): 
        if nombre: 
            registrar_producto(nombre, cantidad, fecha) 
        else: 
            st.warning("Completa todos los campos.") 

# -------REGISTRAR MOVIMIENTO----------- 
if menu == "Registrar Movimiento": 
    st.subheader("Registrar Movimiento de Stock") 
    inventario = cargar_inventario() 
    productos = list(inventario.keys()) 
    
    if not productos: 
        st.info("No hay productos registrados.") 
    else: 
        nombre = st.selectbox("Selecciona el producto", productos) 
        tipo = st.selectbox("Tipo de movimiento", ["Entrada", "Salida"]) 
        cantidad = st.number_input("Cantidad", min_value=1, step=1) 
        
        if st.button("Registrar Movimiento"): 
            registrar_movimiento(nombre, tipo, cantidad) 

# ----------VER INVENTARIO-------- 
if menu == "Ver Inventario": 
    st.subheader("Reporte General de Inventario") 
    inventario = cargar_inventario() 
    
    if not inventario: 
        st.info("No hay productos en el inventario.") 
    else: 
        data = [] 
        for nombre, datos in inventario.items(): 
            movimientos = datos.get("movimientos", [])
            ult_mov = movimientos[-1]["fecha"] if movimientos else "-"
            data.append({ 
                "Producto": nombre, 
                "Cantidad Disponible": datos["cantidad"], 
                "Ultimo Movimiento": ult_mov 
            }) 
        
        st.table(data) 
        
        if st.button("Exportar a PDF"): 
            archivo = exportar_pdf() 
            with open(archivo, "rb") as f: 
                st.download_button("Descargar Reporte PDF", f, file_name=archivo, mime="application/pdf")
