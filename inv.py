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

# --------EXPORTAR REPORTE A PDF (OPTIMIZADO PARA MEMORIA)-------- 
def exportar_pdf(): 
    inventario = cargar_inventario() 
    pdf = FPDF() 
    pdf.add_page() 
    
    pdf.set_font("Arial", 'B', 16) 
    pdf.cell(0, 10, "Reporte de Inventario".encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C') 
    pdf.ln(10) 
    
    pdf.set_font("Arial", 'B', 10) 
    pdf.cell(60, 10, "Producto".encode('latin-1', 'replace').decode('latin-1'), 1) 
    pdf.cell(30, 10, "Cantidad".encode('latin-1', 'replace').decode('latin-1'), 1) 
    pdf.cell(80, 10, "Ultimo Movimiento".encode('latin-1', 'replace').decode('latin-1'), 1) 
    pdf.ln() 
    
    pdf.set_font("Arial", '', 10) 
    for nombre, datos in inventario.items(): 
        movimientos = datos.get("movimientos", [])
        ult_mov = movimientos[-1]["fecha"] if movimientos else "-"
        
        nombre_limpio = nombre.encode('latin-1', 'replace').decode('latin-1')
        ult_mov_limpio = str(ult_mov).encode('latin-1', 'replace').decode('latin-1')
        
        pdf.cell(60, 10, nombre_limpio, 1) 
        pdf.cell(30, 10, str(datos["cantidad"]), 1) 
        pdf.cell(80, 10, ult_mov_limpio, 1) 
        pdf.ln() 
        
    return pdf.output(dest='S').encode('latin-1')

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

# ----------VER E INFORMAR INVENTARIO (MODIFICABLE)-------- 
if menu == "Ver Inventario": 
    st.subheader("Reporte General de Inventario") 
    st.caption("💡 Haz doble clic sobre cualquier celda para corregir errores. Al terminar, presiona Ctrl+Enter o haz clic fuera.")
    
    inventario = cargar_inventario() 
    
    if not inventario: 
        st.info("No hay productos en el inventario.") 
    else: 
        # Convertimos el diccionario a una lista para el editor interactivo
        lista_productos = [] 
        for nombre, datos in inventario.items(): 
            movimientos = datos.get("movimientos", [])
            ult_mov = movimientos[-1]["fecha"] if movimientos else "-"
            lista_productos.append({ 
                "Producto Original": nombre,  # Columna oculta de control
                "Producto": nombre, 
                "Cantidad Disponible": datos["cantidad"], 
                "Último Movimiento": ult_mov 
            }) 
        
        # El componente st.data_editor permite modificar datos directo en pantalla
        tabla_editada = st.data_editor(
            lista_productos, 
            column_config={
                "Producto Original": None,  # Ocultamos esta columna
                "Último Movimiento": st.column_config.TextColumn(disabled=True)  # No editable por seguridad
            },
            hide_index=True,
            use_container_width=True
        ) 
        
        # Detectar si la tabla cambió para actualizar el archivo JSON
        if tabla_editada != lista_productos:
            nuevo_inventario = {}
            for fila in tabla_editada:
                id_original = fila["Producto Original"]
                nuevo_nombre = fila["Producto"]
                nueva_cantidad = fila["Cantidad Disponible"]
                
                # Si el producto ya existía, conservamos su historial de movimientos
                if id_original in inventario:
                    nuevo_inventario[nuevo_nombre] = inventario[id_original]
                    nuevo_inventario[nuevo_nombre]["cantidad"] = nueva_cantidad
                else:
                    # En caso de fallas de sincronización crea una base limpia
                    nuevo_inventario[nuevo_nombre] = {
                        "cantidad": nueva_cantidad,
                        "fecha_ingreso": datetime.now().strftime('%Y-%m-%d'),
                        "movimientos": []
                    }
            
            guardar_inventario(nuevo_inventario)
            st.success("¡Inventario actualizado correctamente!")
            st.rerun()  # Recarga la app para aplicar visualmente los cambios
        
        # Botón de PDF unificado (Un solo clic genera y descarga)
        pdf_bytes = exportar_pdf() 
        st.download_button(
            label="Descargar Reporte PDF", 
            data=pdf_bytes, 
            file_name="reporte_inventario.pdf", 
            mime="application/pdf"
        )
