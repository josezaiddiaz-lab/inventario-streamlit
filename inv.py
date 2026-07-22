import streamlit as st 
import pandas as pd
from datetime import datetime 
from fpdf import FPDF 
from streamlit_gsheets import GSheetsConnection
import io

# =========================
# 🔐 SESSION STATE
# =========================
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
if "usuario" not in st.session_state:
    st.session_state["usuario"] = ""
if "rol" not in st.session_state:
    st.session_state["rol"] = ""
if "log" not in st.session_state:
    st.session_state["log"] = []

# =========================
# 🔐 USUARIOS
# =========================
USUARIOS = {
    "admin": {"password": "1234", "rol": "admin"},
    "jdiaz": {"password": "1978", "rol": "usuario"}
}

def registrar_accion(accion):
    st.session_state["log"].append({
        "usuario": st.session_state.get("usuario",""),
        "rol": st.session_state.get("rol",""),
        "accion": accion,
        "hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

# =========================
# 🔐 LOGIN
# =========================
def login():
    st.title("🔐 Iniciar sesión")

    user = st.text_input("Usuario")
    pwd = st.text_input("Contraseña", type="password")

    if st.button("Entrar"):
        if user in USUARIOS and USUARIOS[user]["password"] == pwd:
            st.session_state["autenticado"] = True
            st.session_state["usuario"] = user
            st.session_state["rol"] = USUARIOS[user]["rol"]
            registrar_accion("Login")
            st.rerun()
        else:
            st.error("Datos incorrectos")

if not st.session_state["autenticado"]:
    login()
    st.stop()

# =========================
# SIDEBAR
# =========================
st.sidebar.write(f"👤 Usuario: {st.session_state.get('usuario','')}")
st.sidebar.write(f"🔑 Rol: {st.session_state.get('rol','')}")

if st.sidebar.button("Cerrar sesión"):
    registrar_accion("Logout")
    st.session_state["autenticado"] = False
    st.session_state["usuario"] = ""
    st.session_state["rol"] = ""
    st.rerun()

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Inventario", layout="centered")

# =========================
# GOOGLE SHEETS
# =========================
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_inventario_dataframe():
    try:
        df = conn.read(worksheet="Productos", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=["PRODUCTO","CANTIDAD_ACTUAL","ALMACEN","FECHA_INGRESO"])
        return df
    except:
        return pd.DataFrame(columns=["PRODUCTO","CANTIDAD_ACTUAL","ALMACEN","FECHA_INGRESO"])

def cargar_historial_dataframe():
    try:
        df = conn.read(worksheet="Historial", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=["PRODUCTO","TIPO","CANTIDAD","FECHA"])
        return df
    except:
        return pd.DataFrame(columns=["PRODUCTO","TIPO","CANTIDAD","FECHA"])

def limpiar_texto_pdf(texto):
    return str(texto).encode('latin-1', 'replace').decode('latin-1')

# =========================
# 📄 EXPORTAR
# =========================
def convertir_a_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

def convertir_a_pdf(df, titulo="Reporte"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)

    pdf.cell(200,10, limpiar_texto_pdf(titulo), ln=True, align="C")

    for col in df.columns:
        pdf.cell(40,8, limpiar_texto_pdf(col), border=1)
    pdf.ln()

    for _, row in df.iterrows():
        for item in row:
            pdf.cell(40,8, limpiar_texto_pdf(item), border=1)
        pdf.ln()

    return pdf.output(dest='S').encode('latin-1')

# =========================
# FUNCIONES
# =========================
def registrar_producto(nombre, cantidad, fecha, almacen):
    if st.session_state["rol"] != "admin":
        st.error("Solo admin")
        return

    df = cargar_inventario_dataframe()
    nombre = nombre.upper()

    nuevo = pd.DataFrame([{
        "PRODUCTO": nombre,
        "CANTIDAD_ACTUAL": int(cantidad),
        "ALMACEN": almacen,
        "FECHA_INGRESO": fecha
    }])

    conn.update("Productos", pd.concat([df, nuevo]).astype(str))
    registrar_accion(f"Producto {nombre}")

def registrar_movimiento(nombre, tipo, cantidad):
    df = cargar_inventario_dataframe()

    idx = df[df["PRODUCTO"] == nombre].index[0]
    actual = int(df.loc[idx,"CANTIDAD_ACTUAL"])

    nueva = actual + cantidad if tipo=="Entrada" else actual - cantidad
    df.loc[idx,"CANTIDAD_ACTUAL"] = nueva

    conn.update("Productos", df.astype(str))
    registrar_accion(f"{tipo} {cantidad} {nombre}")

# =========================
# UI
# =========================
st.title("📦 Inventario")

menu = st.sidebar.selectbox("Menú", [
    "Registrar Producto",
    "Movimiento",
    "Ver Inventario",
    "Historial",
    "Pedidos"
])

# =========================
# REGISTRAR PRODUCTO
# =========================
if menu == "Registrar Producto":
    nombre = st.text_input("Nombre")
    cantidad = st.number_input("Cantidad", 0)
    almacen = st.number_input("Almacén", 1)
    fecha = st.date_input("Fecha")

    if st.button("Guardar"):
        registrar_producto(nombre, cantidad, str(fecha), almacen)

# =========================
# MOVIMIENTO
# =========================
elif menu == "Movimiento":
    df = cargar_inventario_dataframe()
    if not df.empty:
        nombre = st.selectbox("Producto", df["PRODUCTO"])
        tipo = st.radio("Tipo", ["Entrada","Salida"])
        cantidad = st.number_input("Cantidad", 1)

        if st.button("Aplicar"):
            registrar_movimiento(nombre, tipo, cantidad)

# =========================
# INVENTARIO
# =========================
elif menu == "Ver Inventario":
    df = cargar_inventario_dataframe()
    st.dataframe(df)

    if not df.empty:
        st.download_button("Excel", convertir_a_excel(df), "inventario.xlsx")
        st.download_button("PDF", convertir_a_pdf(df,"Inventario"), "inventario.pdf")

# =========================
# HISTORIAL
# =========================
elif menu == "Historial":
    df = cargar_historial_dataframe()
    st.dataframe(df)

    if not df.empty:
        st.download_button("Excel", convertir_a_excel(df), "historial.xlsx")
        st.download_button("PDF", convertir_a_pdf(df,"Historial"), "historial.pdf")

# =========================
# PEDIDOS
# =========================
elif menu == "Pedidos":
    df = cargar_inventario_dataframe()
    bajos = df[df["CANTIDAD_ACTUAL"].astype(int) <= 1]

    st.dataframe(bajos)

    if not bajos.empty:
        st.download_button("Excel", convertir_a_excel(bajos), "pedidos.xlsx")
        st.download_button("PDF", convertir_a_pdf(bajos,"Pedidos"), "pedidos.pdf")

# =========================
# LOG
# =========================
if st.session_state["rol"] == "admin":
    st.subheader("Actividad")
    st.dataframe(st.session_state["log"])