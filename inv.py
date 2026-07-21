import streamlit as st
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
import io

# ---------------- FUNCIONES BASE ---------------- #

def cargar_inventario():
    if "inventario" not in st.session_state:
        st.session_state.inventario = {}
    return st.session_state.inventario

def limpiar_entero(valor):
    try:
        return int(valor)
    except:
        return 0

# ---------------- EXPORTAR PDF ---------------- #

def exportar_pdf():
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    inventario = cargar_inventario()

    data = [["PRODUCTO", "CANTIDAD", "ULTIMO MOVIMIENTO"]]

    for nombre, datos in inventario.items():
        data.append([
            nombre.upper(),
            limpiar_entero(datos.get("cantidad", 0)),
            datos.get("ultimo_movimiento", "")
        ])

    tabla = Table(data)

    estilo = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 1, colors.black)
    ])

    tabla.setStyle(estilo)
    doc.build([tabla])

    pdf = buffer.getvalue()
    buffer.close()
    return pdf

# ---------------- PDF PEDIDOS ---------------- #

def exportar_pdf_pedidos():
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    inventario = cargar_inventario()

    data = [["PRODUCTO", "CANTIDAD DISPONIBLE"]]

    for nombre, datos in inventario.items():
        cantidad = limpiar_entero(datos.get("cantidad", 0))
        if cantidad <= 1:
            data.append([nombre.upper(), cantidad])

    tabla = Table(data)

    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.red),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 1, colors.black)
    ]))

    doc.build([tabla])

    pdf = buffer.getvalue()
    buffer.close()
    return pdf

# ---------------- MENÚ ---------------- #

menu = st.sidebar.selectbox("Menú", [
    "Ver Inventario",
    "Agregar Producto",
    "Editar Producto",
    "Solicitar Pedidos"
])

# ---------------- VER INVENTARIO ---------------- #

if menu == "Ver Inventario":
    st.subheader("Inventario Actual")

    inventario = cargar_inventario()
    tabla = []

    for nombre, datos in inventario.items():
        tabla.append({
            "PRODUCTO": nombre.upper(),
            "CANTIDAD": limpiar_entero(datos.get("cantidad", 0)),
            "ULTIMO MOVIMIENTO": datos.get("ultimo_movimiento", "")
        })

    st.table(tabla)

    pdf_bytes = exportar_pdf()

    st.download_button(
        label="Descargar Reporte PDF",
        data=pdf_bytes,
        file_name="reporte_inventario.pdf",
        mime="application/pdf"
    )

# ---------------- AGREGAR PRODUCTO ---------------- #

elif menu == "Agregar Producto":
    st.subheader("Agregar Producto")

    nombre = st.text_input("Nombre del producto")
    cantidad = st.number_input("Cantidad", min_value=0)

    if st.button("Agregar"):
        inventario = cargar_inventario()

        inventario[nombre.upper()] = {
            "cantidad": cantidad,
            "ultimo_movimiento": "Entrada"
        }

        st.success("Producto agregado correctamente")

# ---------------- EDITAR PRODUCTO (CORRECCIÓN) ---------------- #

elif menu == "Editar Producto":
    st.subheader("Corregir Nombre de Producto")

    inventario = cargar_inventario()

    if inventario:
        producto = st.selectbox("Selecciona producto", list(inventario.keys()))
        nuevo_nombre = st.text_input("Nuevo nombre")

        if st.button("Actualizar"):
            if nuevo_nombre:
                inventario[nuevo_nombre.upper()] = inventario.pop(producto)
                st.success("Producto actualizado correctamente")
    else:
        st.warning("No hay productos para editar")

# ---------------- SOLICITAR PEDIDOS ---------------- #

elif menu == "Solicitar Pedidos":
    st.subheader("Productos por Agotarse (Stock en 0 o 1)")

    inventario = cargar_inventario()
    productos_bajos = []

    for nombre, datos in inventario.items():
        cant_evaluar = limpiar_entero(datos.get("cantidad", 0))

        if cant_evaluar <= 1:
            productos_bajos.append({
                "PRODUCTO": nombre.upper(),
                "CANTIDAD DISPONIBLE": cant_evaluar
            })

    if not productos_bajos:
        st.success("✅ ¡Excelente! Todos tus productos tienen buen stock.")
    else:
        st.error(f"⚠️ {len(productos_bajos)} producto(s) requieren pedido.")
        st.table(productos_bajos)

        pdf_bytes_pedidos = exportar_pdf_pedidos()

        st.download_button(
            label="Descargar Reporte de Pedidos PDF",
            data=pdf_bytes_pedidos,
            file_name="reporte_pedidos.pdf",
            mime="application/pdf"
        )