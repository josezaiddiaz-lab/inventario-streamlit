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

# --------INTERFAZ STREAMLIT---------- 
st.set_page_config(page_title="Control de Inventario GCM", layout="centered") 
st.title("Control de Inventario GCM") 

menu = st.sidebar.selectbox(
    "Selecciona una opción", 
    ["Registrar Producto", "Registrar Movimiento", "Ver Inventario"]
)

# --------REGISTRAR PRODUCTO--------
if menu == "Registrar Producto": 
    st.subheader("Registrar Nuevo Producto") 

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
            st.warning("Completa todos los campos")

    st.text_input("Nombre del producto", key="nombre") 
    st.number_input("Cantidad inicial", min_value=0, step=1, key="cantidad") 
    st.selectbox("Almacén", [1, 2, 3, 4, 5, 6], key="almacen")

    st.button("Registrar Producto", on_click=registrar_y_limpiar)

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

    st.subheader("📋 Inventario Actual")

    if len(inventario) == 0:
        st.info("No hay productos registrados.")
    else:
        lista = []
        for prod, datos in inventario.items():
            lista.append({
                "Producto Original": prod,
                "PRODUCTO": prod,
                "CANTIDAD": datos["cantidad"],
                "ALMACÉN": datos["almacen"],
                "ULTIMO MOVIMIENTO": datos["movimientos"][-1] if datos["movimientos"] else ""
            })

        # CSS PARA CENTRAR TODA LA COLUMNA
        st.markdown("""
        <style>
        /* Centrar TODO en columnas 3 y 4 */
        [data-testid="stDataFrame"] th:nth-child(3),
        [data-testid="stDataFrame"] th:nth-child(4),
        [data-testid="stDataFrame"] td:nth-child(3),
        [data-testid="stDataFrame"] td:nth-child(4) {
            text-align: center !important;
        }

        /* Centrar contenido dentro de inputs (cuando editas) */
        [data-testid="stDataFrame"] td:nth-child(3) input,
        [data-testid="stDataFrame"] td:nth-child(4) input {
            text-align: center !important;
        }

        /* Centrar dropdown (almacén) */
        [data-testid="stDataFrame"] td:nth-child(4) div {
            justify-content: center !important;
        }
        </style>
        """, unsafe_allow_html=True)

        tabla = st.data_editor(
            lista,
            column_config={
                "Producto Original": None,
                "PRODUCTO": st.column_config.TextColumn(),
                "CANTIDAD": st.column_config.NumberColumn(),
                "ALMACÉN": st.column_config.SelectboxColumn(
                    options=[1, 2, 3, 4, 5, 6],
                    required=True
                ),
                "ULTIMO MOVIMIENTO": st.column_config.TextColumn(disabled=True)
            },
            hide_index=True,
            use_container_width=True
        )

        if st.button(" Guardar cambios"):
            nuevo_inventario = {}

            for fila in tabla:
                nombre = fila["PRODUCTO"].strip().upper()
                cantidad = int(fila["CANTIDAD"])
                almacen = int(fila["ALMACÉN"])
                original = fila["Producto Original"]

                movimientos = inventario.get(original, {}).get("movimientos", [])
                movimientos.append("Edición manual")

                nuevo_inventario[nombre] = {
                    "cantidad": cantidad,
                    "almacen": almacen,
                    "movimientos": movimientos
                }

            inventario = nuevo_inventario
            guardar_datos(inventario)
            st.success("Inventario actualizado correctamente")