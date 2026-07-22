import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF
from streamlit_gsheets import GSheetsConnection
import io

# =========================
# 🔐 INICIALIZAR SESSION STATE (FIX ERROR)
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

# =========================
# 📊 LOG
# =========================
def registrar_accion(accion):
    st.session_state["log"].append({
        "usuario": st.session_state.get("usuario", ""),
        "rol": st.session_state.get("rol", ""),
        "accion": accion,
        "hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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

            registrar_accion("Login")
            st.rerun()
        else:
            st.error("Credenciales incorrectas")

# =========================
# 🔒 CONTROL LOGIN
# =========================
if not st.session_state["autenticado"]:
    login()
    st.stop()

# =========================
# 🔓 SIDEBAR (YA SEGURO)
# =========================
st.sidebar.write(f"👤 Usuario: {st.session_state.get('usuario', '')}")
st.sidebar.write(f"🔑 Rol: {st.session_state.get('rol', '')}")

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
        return df if df is not None else pd.DataFrame()
    except:
        return pd.DataFrame()

# =========================
# FUNCIONES
# =========================
def registrar_producto(nombre, cantidad):
    if st.session_state["rol"] != "admin":
        st.error("No tienes permisos")
        return

    df = cargar_inventario_dataframe()

    nuevo = pd.DataFrame([{
        "PRODUCTO": nombre.upper(),
        "CANTIDAD_ACTUAL": int(cantidad)
    }])

    conn.update("Productos", pd.concat([df, nuevo]).astype(str))
    registrar_accion(f"Agregó {nombre}")
    st.success("Producto agregado")

def registrar_movimiento(nombre, cantidad, tipo):
    df = cargar_inventario_dataframe()

    if nombre not in df["PRODUCTO"].values:
        st.error("No existe")
        return

    idx = df[df["PRODUCTO"] == nombre].index[0]
    actual = int(df.loc[idx, "CANTIDAD_ACTUAL"])

    if tipo == "Salida" and cantidad > actual:
        st.error("Sin stock")
        return

    nueva = actual + cantidad if tipo == "Entrada" else actual - cantidad
    df.loc[idx, "CANTIDAD_ACTUAL"] = nueva

    conn.update("Productos", df.astype(str))
    registrar_accion(f"{tipo} {cantidad} {nombre}")
    st.success("Movimiento realizado")

# =========================
# UI
# =========================
st.title("📦 Inventario")

menu = st.sidebar.selectbox("Menú", [
    "Registrar Producto",
    "Movimiento",
    "Ver Inventario"
])

# =========================
# REGISTRAR PRODUCTO
# =========================
if menu == "Registrar Producto":
    if st.session_state["rol"] != "admin":
        st.warning("Solo admin")
    else:
        nombre = st.text_input("Nombre")
        cantidad = st.number_input("Cantidad", 0)

        if st.button("Guardar"):
            registrar_producto(nombre, cantidad)

# =========================
# MOVIMIENTO
# =========================
elif menu == "Movimiento":
    df = cargar_inventario_dataframe()

    if not df.empty:
        nombre = st.selectbox("Producto", df["PRODUCTO"])
        tipo = st.radio("Tipo", ["Entrada", "Salida"])
        cantidad = st.number_input("Cantidad", 1)

        if st.button("Aplicar"):
            registrar_movimiento(nombre, cantidad, tipo)

# =========================
# VER INVENTARIO
# =========================
elif menu == "Ver Inventario":
    df = cargar_inventario_dataframe()
    st.dataframe(df)

# =========================
# LOG ADMIN
# =========================
if st.session_state["rol"] == "admin":
    st.subheader("📊 Actividad")
    st.dataframe(st.session_state["log"])