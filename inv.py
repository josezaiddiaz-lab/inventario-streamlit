import streamlit as st
import json
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO

ARCHIVO = "inventario.json"

# ---------------- FUNCIONES ----------------

def cargar_inventario():
    try:
        with open(ARCHIVO, "r") as f:
            return json.load(f)
    except:
        return {}

def guardar_inventario(data):
    with open(ARCHIVO, "w") as f:
        json.dump(data, f, indent=4)

def limpiar_entero(valor):
    try:
        return int(valor)
    except:
        return 0

def exportar_pdf_pedidos():
    inventario = cargar_inventario()

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)

    y = 750
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(200, y, "REPORTE DE PEDIDOS")
    y -= 40

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(50, y, "PRODUCTO")
    pdf.drawString(250, y, "CANTIDAD")
    y -= 20

    pdf.setFont("Helvetica", 10)

    for nombre, datos in inventario.items():
        cantidad = limpiar_entero(datos.get("cantidad", 0))

        if cantidad <= 1:
            pdf.drawString(50, y, nombre.upper())
            pdf.drawString(250, y, str(cantidad))
            y -= 20

    pdf.save()
    buffer.seek(0)
    return buffer

# ---------------- MENU ----------------

menu = st.sidebar.selectbox("MENÚ", [
    "Editar Inventario",
    "Solicitar Pedidos"
])

# ---------------- EDITAR INVENTARIO ----------------

if menu == "Editar Inventario":

    st.subheader("✏️ EDITAR INVENTARIO")

    inventario = cargar_inventario()

    lista = []
    for nombre, datos in inventario.items():
        lista.append({
            "Producto Original": nombre,
            "PRODUCTO": nombre,
            "CANTIDAD": limpiar_entero(datos.get("cantidad", 0)),
            "ALMACÉN": limpiar_entero(datos.get("almacen", 1)) or 1,
            "ULTIMO MOVIMIENTO": datos.get("ultimo_movimiento", "")
        })

    tabla = st.data_editor(
        lista,
        column_config={
            "Producto Original": None,
            "CANTIDAD": st.column_config.NumberColumn(disabled=True),
            "ALMACÉN": st.column_config.NumberColumn(min_value=1, max_value=4),
            "ULTIMO MOVIMIENTO": st.column_config.TextColumn(disabled=True)
        },
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic"
    )

    col1, col2 = st.columns(2)

    # -------- GUARDAR --------
    with col1:
        if st.button("💾 GUARDAR CAMBIOS"):
            nuevo = {}
            nombres_vistos = set()
            error = False

            for fila in tabla:
                original = fila["Producto Original"]
                nuevo_nombre = fila["PRODUCTO"].strip().upper()

                if not nuevo_nombre:
                    st.error("❌ No puede haber nombres vacíos")
                    error = True
                    break

                if nuevo_nombre in nombres_vistos:
                    st.error(f"❌ Nombre duplicado: {nuevo_nombre}")
                    error = True
                    break

                nombres_vistos.add(nuevo_nombre)

                if original not in inventario:
                    nuevo[nuevo_nombre] = {
                        "cantidad": 0,
                        "almacen": fila["ALMACÉN"] or 1,
                        "ultimo_movimiento": "Producto agregado"
                    }
                else:
                    nuevo[nuevo_nombre] = inventario[original]
                    nuevo[nuevo_nombre]["almacen"] = fila["ALMACÉN"] or 1

            if not error:
                guardar_inventario(nuevo)
                st.success("✅ Cambios guardados correctamente")
                st.rerun()

    # -------- ELIMINAR --------
    with col2:
        productos_actuales = [fila["PRODUCTO"] for fila in tabla]

        eliminar = st.multiselect(
            "🗑️ Selecciona productos a eliminar",
            productos_actuales
        )

        if st.button("ELIMINAR SELECCIONADOS"):
            if eliminar:
                nuevo = {}

                for fila in tabla:
                    nombre = fila["PRODUCTO"]
                    original = fila["Producto Original"]

                    if nombre not in eliminar:
                        if original in inventario:
                            nuevo[nombre] = inventario[original]
                        else:
                            nuevo[nombre] = {
                                "cantidad": 0,
                                "almacen": fila["ALMACÉN"] or 1,
                                "ultimo_movimiento": "Producto agregado"
                            }

                guardar_inventario(nuevo)
                st.success("🗑️ Productos eliminados")
                st.rerun()
            else:
                st.warning("⚠️ Selecciona al menos un producto")

# ---------------- PEDIDOS ----------------

if menu == "Solicitar Pedidos":

    st.subheader("📦 PRODUCTOS POR AGOTARSE")

    inventario = cargar_inventario()

    productos_bajos = []

    for nombre, datos in inventario.items():
        cant = limpiar_entero(datos.get("cantidad", 0))

        if cant <= 1:
            productos_bajos.append({
                "PRODUCTO": nombre.upper(),
                "CANTIDAD DISPONIBLE": cant
            })

    if not productos_bajos:
        st.success("✅ Todos los productos tienen buen stock")
    else:
        st.error(f"⚠️ {len(productos_bajos)} producto(s) requieren pedido")
        st.table(productos_bajos)

        pdf = exportar_pdf_pedidos()

        st.download_button(
            "📄 DESCARGAR PDF",
            data=pdf,
            file_name="reporte_pedidos.pdf",
            mime="application/pdf"
        )