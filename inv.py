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

# Función auxiliar de seguridad para convertir cualquier dato raro a número entero
def limpiar_entero(valor):
    try:
        return int(valor)
    except (ValueError, TypeError):
        return 0

# ---------REGISTRO DE NUEVO PRODUCTO (FORZADO A MAYÚSCULAS)----------- 
def registrar_producto(nombre, cantidad, fecha): 
    inventario = cargar_inventario() 
    nombre_mayus = nombre.strip().upper()
    
    if nombre_mayus in inventario: 
        st.warning("El producto ya existe en el inventario.") 
        return 
    
    cant_limpia = limpiar_entero(cantidad)
    inventario[nombre_mayus] = { 
        "cantidad": cant_limpia, 
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
        cant_mostrar = limpiar_entero(datos.get("cantidad", 0))
        
        nombre_limpio = nombre.encode('latin-1', 'replace').decode('latin-1')
        ult_mov_limpio = str(ult_mov).encode('latin-1', 'replace').decode('latin-1')
        
        pdf.cell(60, 10, nombre_limpio, 1) 
        pdf.cell(30, 10, str(cant_mostrar), 1) 
        pdf.cell(80, 10, ult_mov_limpio, 1) 
        pdf.ln() 
        
    return bytes(pdf.output(dest='S'))

# --------EXPORTAR REPORTE DE PEDIDOS A PDF-------- 
def exportar_pdf_pedidos(): 
    inventario = cargar_inventario() 
    pdf = FPDF() 
    pdf.add_page() 
    
    pdf.set_font("Arial", 'B', 16) 
    pdf.cell(0, 10, "Reporte de Pedidos Solicitados".encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C') 
    pdf.ln(10) 
    
    pdf.set_font("Arial", 'B', 10) 
    pdf.cell(100, 10, "Producto".encode('latin-1', 'replace').decode('latin-1'), 1) 
    pdf.cell(50, 10, "Cantidad Disponible".encode('latin-1', 'replace').decode('latin-1'), 1) 
    pdf.ln() 
    
    pdf.set_font("Arial", '', 10) 
    for nombre, datos in inventario.items(): 
        cant_evaluar = limpiar_entero(datos.get("cantidad", 0))
        if cant_evaluar <= 1: 
            nombre_limpio = nombre.encode('latin-1', 'replace').decode('latin-1')
            pdf.cell(100, 10, nombre_limpio, 1) 
            pdf.cell(50, 10, str(cant_evaluar), 1) 
            pdf.ln() 
            
    return bytes(pdf.output(dest='S'))

# --------INTERFAZ STREAMLIT---------- 
st.set_page_config(page_title="Control de Inventario", layout="centered") 
st.title("Control de Inventario") 

menu = st.sidebar.selectbox("Selecciona una opción", ["Registrar Producto", "Registrar Movimiento", "Ver Inventario", "Solicitar Pedidos"]) 

# -------REGISTRAR PRODUCTO--------- 
if menu == "Registrar Producto": 
    st.subheader("Registrar Nuevo Producto") 
    nombre = st.text_input("Nombre del producto") 
    cantidad = st.number_input("Cantidad inicial", min_value=0, step=1) 
    fecha = st.date_input("Fecha de ingreso", value=datetime.now()).strftime('%Y-%m-%d') 
    
    if st.button("Registrar Producto"): 
        if nombre: 
            registrar_producto(nombre, cantidad=cantidad, fecha=fecha) 
        else: 
            st.warning("Completa todos los campos.") 

# -------REGISTRAR MOVIMIENTO----------- 
if menu == "Registrar Movimiento": 
    st.subheader("Registrar Movimiento de Stock") 
    inventario = cargar_inventario() 
    productos = sorted(list(inventario.keys())) 
    
    if not productos: 
        st.info("No hay productos registrados.") 
    else: 
        nombre = st.selectbox(
            "Selecciona o busca el producto", 
            options=productos,
            index=None,  
            placeholder="Escribe para buscar... (ej: TN)"
        ) 
        
        tipo = st.radio(
            "Tipo de movimiento", 
            options=["Entrada", "Salida"],
            horizontal=True  
        ) 
        
        cantidad = st.number_input("Cantidad", min_value=1, step=1) 
        
        if st.button("Registrar Movimiento"): 
            if nombre:
                registrar_movimiento(nombre, tipo, cantidad) 
            else:
                st.warning("Por favor, selecciona un producto válido de la lista.")

# ----------VER E INFORMAR INVENTARIO (CONVERTIDOR A MAYÚSCULAS)-------- 
if menu == "Ver Inventario": 
    st.subheader("Reporte General de Inventario") 
    st.caption("💡 Haz doble clic sobre la celda de Producto para corregir su nombre. Las cantidades solo se modifican registrando movimientos.")
    
    inventario = cargar_inventario() 
    
    if not inventario: 
        st.info("No hay productos en el inventario.") 
    else: 
        lista_productos = [] 
        for nombre, datos in inventario.items(): 
            movimientos = datos.get("movimientos", [])
            ult_mov = movimientos[-1]["fecha"] if movimientos else "-"
            
            if len(ult_mov) > 10:
                ult_mov = ult_mov[:10]
                
            lista_productos.append({ 
                "Producto Original": nombre, 
                "Producto": nombre, 
                "Cantidad Disponible": limpiar_entero(datos.get("cantidad", 0)), 
                "Último Movimiento": ult_mov 
            }) 
        
        tabla_editada = st.data_editor(
            lista_productos, 
            column_config={
                "Producto Original": None, 
                "Cantidad Disponible": st.column_config.NumberColumn(disabled=True),
                "Último Movimiento": st.column_config.TextColumn(disabled=True)
            },
            hide_index=True,
            use_container_width=True
        ) 
        
        if tabla_editada != lista_productos:
            nuevo_inventario = {}
            error_duplicado = False
            nombre_duplicado = ""
            
            nombres_vistos = set()
            for fila in tabla_editada:
                nuevo_nombre = fila["Producto"].strip().upper()
                id_original = fila["Producto Original"]
                
                if nuevo_nombre in inventario and nuevo_nombre != id_original:
                    error_duplicado = True
                    nombre_duplicado = nuevo_nombre
                    break
                
                if nuevo_nombre in nombres_vistos:
                    error_duplicado = True
                    nombre_duplicado = nuevo_nombre
                    break
                nombres_vistos.add(nuevo_nombre)
            
            if error_duplicado:
                st.error(f"❌ Error: El producto '{nombre_duplicado}' ya se encuentra registrado en la lista. No se guardaron los cambios.")
            else:
                for fila in tabla_editada:
                    id_original = fila["Producto Original"]
                    nuevo_nombre = fila["Producto"].strip().upper()
                    nueva_cantidad = limpiar_entero(fila["Cantidad Disponible"])
                    
                    if id_original in inventario:
                        nuevo_inventario[nuevo_nombre] = inventario[id_original]
                        nuevo_inventario[nuevo_nombre]["cantidad"] = nueva_cantidad
                    else:
                        nuevo_inventario[nuevo_nombre] = {
                            "cantidad": nueva_cantidad,
                            "fecha_ingreso": datetime.now().strftime('%Y-%m-%d'),
                            "movimientos": []
                        }
                
                guardar_inventario(nuevo_inventario)
                st.success("¡Nombre del producto actualizado correctamente!")
