import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF
from streamlit_gsheets import GSheetsConnection
import io

# =========================
# 🔐 USUARIOS CON ROLES
# =========================
USUARIOS = {
    "admin": {"password": "1234", "rol": "admin"},
    "jdiaz": {"password": "1978", "rol": "usuario"}
}

# =========================
# 📊 LOG DE ACTIVIDAD
# =========================
if "log" not in st.session_state:
    st.session_state["log"] = []

def registrar_accion(accion):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    usuario = st.session_state.get("usuario", "desconocido")
    rol = st.session_state.get("rol", "sin rol")

    st.session_state["log"].append({
        "usuario": usuario,
        "rol": rol,
        "accion": accion,
        "hora": timestamp
    })

# =========================
# 🔐 LOGIN
# =========================
def login():
    st.title("🔐 Iniciar sesión")

    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Entrar"):
        if usuario in USUARIOS and USUARIOS[usuario]["password"] == password:
            st.session_state["autenticado"] = True
            st.session_state["usuario"] = usuario
            st.session_state["rol"] = USUARIOS[usuario]["rol"]

            registrar_accion("Inició sesión")
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")

# =========================
# 🔒 CONTROL DE SESIÓN
# =========================
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    login()
    st.stop()

# =========================
# 🔓 SIDEBAR
# =========================
st.sidebar.write(f"👤 Usuario: {st.session_state['usuario']}")
st.sidebar.write(f"🔑 Rol: {st.session_state['rol']}")

if st.sidebar.button("🔓 Cerrar sesión"):
    registrar_accion("Cerró sesión")
    st.session_state["autenticado"] = False
    st.rerun()

# =========================
# CONFIGURACIÓN DE PÁGINA
# =========================
st.set_page_config(
    page_title="Control de Inventario GCM",
    layout="centered",
    initial_sidebar_state="expanded"
)

# =========================
# CONEXIÓN GOOGLE SHEETS
# =========================
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_inventario_dataframe():
    try:
        df = conn.read(worksheet="Productos", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=["PRODUCTO", "CANTIDAD_ACTUAL", "ALMACEN", "FECHA_INGRESO"])
        return df
    except:
        return pd.DataFrame(columns=["PRODUCTO", "CANTIDAD_ACTUAL", "ALMACEN", "FECHA_INGRESO"])

def cargar_historial_dataframe():
    try:
        df = conn.read(worksheet="Historial", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=["PRODUCTO", "TIPO", "CANTIDAD", "FECHA"])
        return df
    except:
        return pd.DataFrame(columns=["PRODUCTO", "TIPO", "CANTIDAD", "FECHA"])

def limpiar_entero(valor):
    try:
        return int(valor)
    except:
        return 0

def limpiar_texto_pdf(texto):
    return str(texto).encode('latin-1', 'replace').decode('latin-1')

# =========================
# REGISTRAR PRODUCTO
# =========================
def registrar_producto(nombre, cantidad, fecha, almacen):

    if st.session_state["rol"] != "admin":
        st.error("❌ No tienes permiso")
        return False

    df_productos = cargar_inventario_dataframe()
    nombre = nombre.strip().upper()

    if not df_productos.empty and nombre in df_productos["PRODUCTO"].values:
        st.warning("El producto ya existe")
        return False

    nuevo = pd.DataFrame([{
        "PRODUCTO": nombre,
        "CANTIDAD_ACTUAL": limpiar_entero(cantidad),
        "ALMACEN": almacen,
        "FECHA_INGRESO": fecha
    }])

    conn.update("Productos", pd.concat([df_productos, nuevo]).astype(str))

    registrar_accion(f"Agregó producto {nombre}")
    return True

# =========================
# MOVIMIENTO
# =========================
def registrar_movimiento(nombre, tipo, cantidad):
    df = cargar_inventario_dataframe()

    if nombre not in df["PRODUCTO"].values:
        st.warning("Producto no encontrado")
        return

    idx = df[df["PRODUCTO"] == nombre].index[0]
    actual = limpiar_entero(df.loc[idx, "CANTIDAD_ACTUAL"])
    cantidad = limpiar_entero(cantidad)

    if tipo == "Salida" and cantidad > actual:
        st.warning("Sin stock")
        return

    nueva = actual + cantidad if tipo == "Entrada" else actual - cantidad
    df.loc[idx, "CANTIDAD_ACTUAL"] = nueva

    conn.update("Productos", df.astype(str))

    registrar_accion(f"{tipo} de {cantidad} en {nombre}")
    st.success("Movimiento registrado")

# =========================
# INTERFAZ
# =========================
st.title("Control de Inventario GCM")

menu = st.sidebar.selectbox(
    "Menú",
    ["Registrar Producto", "Registrar Movimiento", "Ver Inventario"]
)

# =========================
# REGISTRAR PRODUCTO
# =========================
if menu == "Registrar Producto":
    st.subheader("Registrar Producto")

    if st.session_state["rol"] != "admin":
        st.warning("Solo admin puede registrar")
    else:
        nombre = st.text_input("Nombre")
        cantidad = st.number_input("Cantidad", 0)
        almacen = st.number_input("Almacén", 1)
        fecha = st.date_input("Fecha")

        if st.button("Guardar"):
            registrar_producto(nombre, cantidad, str(fecha), almacen)

# =========================
# MOVIMIENTO
# =========================
elif menu == "Registrar Movimiento":
    df = cargar_inventario_dataframe()

    if not df.empty:
        nombre = st.selectbox("Producto", df["PRODUCTO"])
        tipo = st.radio("Tipo", ["Entrada", "Salida"])
        cantidad = st.number_input("Cantidad", 1)

        if st.button("Mover"):
            registrar_movimiento(nombre, tipo, cantidad)

# =========================
# VER INVENTARIO
# =========================
elif menu == "Ver Inventario":
    df = cargar_inventario_dataframe()
    st.dataframe(df)

# =========================
# LOG SOLO ADMIN
# =========================
if st.session_state["rol"] == "admin":
    st.subheader("📊 Registro de actividad")
    st.dataframe(st.session_state["log"])