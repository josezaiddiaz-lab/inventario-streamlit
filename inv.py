import streamlit as st 
import pandas as pd
from datetime import datetime 
from fpdf import FPDF 
from streamlit_gsheets import GSheetsConnection
import io

# ------- CONFIGURACIÓN DE PÁGINA ---------
st.set_page_config(
    page_title="Control de Inventario GCM", 
    layout="centered",
    initial_sidebar_state="expanded"
) 

# 🔐 USUARIOS CON ROLES
USUARIOS = {
    "zaid": {"password": "2010", "rol": "admin"},
    "jdiaz": {"password": "1978", "rol": "usuario"},
    "ccdiazj": {"password": "1974", "rol": "usuario"},
    "gael": {"password": "2003", "rol": "usuario"},
    "monica": {"password": "2026", "rol": "usuario"},
    "sergio": {"password": "sergio2026*", "rol": "usuario"}  # ✅ corregido
}

# 🔐 LOGIN
def login():
    st.title("🔐 Iniciar sesión")

    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Entrar"):
        if usuario in USUARIOS and USUARIOS[usuario]["password"] == password:
            st.session_state["autenticado"] = True
            st.session_state["usuario"] = usuario
            st.session_state["rol"] = USUARIOS[usuario]["rol"]
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")

# 🔒 CONTROL DE SESIÓN
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if "rol" not in st.session_state:
    st.session_state["rol"] = ""

if not st.session_state["autenticado"]:
    login()
    st.stop()

# SIDEBAR
st.sidebar.write(f"👤 Usuario: {st.session_state['usuario']}")
st.sidebar.write(f"🔑 Rol: {st.session_state['rol']}")

if st.sidebar.button("🔓 Cerrar sesión"):
    st.session_state["autenticado"] = False
    st.rerun()

# ------- CONEXIÓN ---------
conn = st.connection("gsheets", type=GSheetsConnection)

# ------- REGISTRO DE ACTIVIDAD ---------
def registrar_accion(accion, cantidad, producto):
    nuevo = pd.DataFrame([{
        "usuario": st.session_state.get("usuario",""),
        "accion": accion,
        "cantidad": cantidad,
        "producto": producto,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }])

    try:
        df_log = conn.read(worksheet="Log", ttl=0)
        if df_log is None:
            df_log = pd.DataFrame(columns=["usuario","accion","cantidad","producto","fecha"])
    except:
        df_log = pd.DataFrame(columns=["usuario","accion","cantidad","producto","fecha"])

    df_log = pd.concat([df_log, nuevo], ignore_index=True)
    conn.update("Log", df_log.astype(str))

# ------- INVENTARIO ---------
def cargar_inventario_dataframe(): 
    try:
        df = conn.read(worksheet="Productos", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=["PRODUCTO", "CANTIDAD_ACTUAL", "ALMACEN", "FECHA_INGRESO"])
        return df
    except:
        return pd.DataFrame(columns=["PRODUCTO", "CANTIDAD_ACTUAL", "ALMACEN", "FECHA_INGRESO"])

def guardar_inventario(df):
    conn.update("Productos", df)

# ------- MENÚ ---------
menu = st.sidebar.selectbox("Menú", [
    "Ver Inventario",
    "Movimientos",
    "Historial de Movimientos",
    "Solicitar Pedidos",
    "Actividad de Usuarios"
])

# ------- VER INVENTARIO ---------
if menu == "Ver Inventario":
    df = cargar_inventario_dataframe()
    st.dataframe(df, use_container_width=True)

# ------- MOVIMIENTOS ---------
elif menu == "Movimientos":
    df = cargar_inventario_dataframe()

    # ✅ Validación si no hay productos
    if df.empty:
        st.warning("No hay productos en el inventario")
        st.stop()

    producto = st.selectbox("Producto", df["PRODUCTO"])
    tipo = st.selectbox("Tipo", ["entrada", "salida"])
    cantidad = st.number_input("Cantidad", min_value=1)

    if st.button("Registrar movimiento"):
        index = df[df["PRODUCTO"] == producto].index[0]

        # ✅ Validación de stock negativo
        if tipo == "salida" and df.at[index, "CANTIDAD_ACTUAL"] < cantidad:
            st.error("No hay suficiente stock")
            st.stop()

        if tipo == "entrada":
            df.at[index, "CANTIDAD_ACTUAL"] += cantidad
        else:
            df.at[index, "CANTIDAD_ACTUAL"] -= cantidad

        guardar_inventario(df)

        registrar_accion(tipo, cantidad, producto)

        st.success("Movimiento registrado")

# ------- HISTORIAL ---------
elif menu == "Historial de Movimientos":
    try:
        df_log = conn.read(worksheet="Log", ttl=0)
        st.dataframe(df_log, use_container_width=True)
    except:
        st.info("Sin datos")

# ------- PEDIDOS ---------
elif menu == "Solicitar Pedidos":
    producto = st.text_input("Producto")
    cantidad = st.number_input("Cantidad", min_value=1)

    if st.button("Solicitar"):
        registrar_accion("pedido", cantidad, producto)
        st.success("Pedido solicitado")

# ------- ACTIVIDAD DE USUARIOS ---------
elif menu == "Actividad de Usuarios":
    if st.session_state["rol"] != "admin":
        st.warning("Solo admin")
    else:
        try:
            df_log = conn.read(worksheet="Log", ttl=0)

            df_log = df_log[["usuario","accion","cantidad","producto","fecha"]]

            df_log["accion"] = df_log["accion"].str.capitalize()

            st.dataframe(
                df_log.sort_values(by="fecha", ascending=False),
                use_container_width=True
            )
        except:
            st.info("Sin actividad registrada")