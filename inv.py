import streamlit as st 
import pandas as pd
from datetime import datetime 
from fpdf import FPDF 
from streamlit_gsheets import GSheetsConnection
import io

# =========================
# 🔐 SESSION STATE (FIX ERROR)
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
# 🔐 USUARIOS CON ROLES
# =========================
USUARIOS = {
    "admin": {"password": "1234", "rol": "admin"},
    "jdiaz": {"password": "1978", "rol": "usuario"}
}

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
            st.error("Usuario o contraseña incorrectos")

if not st.session_state["autenticado"]:
    login()
    st.stop()

# =========================
# SIDEBAR SEGURO
# =========================
st.sidebar.write(f"👤 Usuario: {st.session_state.get('usuario','')}")
st.sidebar.write(f"🔑 Rol: {st.session_state.get('rol','')}")

if st.sidebar.button("🔓 Cerrar sesión"):
    registrar_accion("Logout")
    st.session_state["autenticado"] = False
    st.session_state["usuario"] = ""
    st.session_state["rol"] = ""
    st.rerun()

# =========================
# CONFIG
# =========================
st.set_page_config(
    page_title="Control de Inventario GCM", 
    layout="centered",
    initial_sidebar_state="expanded"
)

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

def limpiar_entero(valor):
    try:
        return int(valor)
    except:
        return 0

def limpiar_texto_pdf(texto):
    return str(texto).encode('latin-1', 'replace').decode('latin-1')

# =========================
# REGISTRAR PRODUCTO (ADMIN)
# =========================
def registrar_producto(nombre, cantidad, fecha, almacen): 

    if st.session_state["rol"] != "admin":
        st.error("❌ Solo admin puede registrar productos")
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

    registrar_accion(f"{tipo} {cantidad} {nombre}")
    st.success("Movimiento registrado")

# =========================
# UI
# =========================
st.title("Control de Inventario GCM")

menu = st.sidebar.selectbox(
    "Selecciona una opción", 
    ["Registrar Producto","Registrar Movimiento","Ver Inventario","Historial de Movimientos","Solicitar Pedidos"]
)

# =========================
# REGISTRAR PRODUCTO
# =========================
if menu == "Registrar Producto":
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
        tipo = st.radio("Tipo", ["Entrada","Salida"])
        cantidad = st.number_input("Cantidad", 1)

        if st.button("Mover"):
            registrar_movimiento(nombre, tipo, cantidad)

# =========================
# INVENTARIO
# =========================
elif menu == "Ver Inventario":
    st.dataframe(cargar_inventario_dataframe())

# =========================
# HISTORIAL (ADMIN)
# =========================
elif menu == "Historial de Movimientos":
    if st.session_state["rol"] != "admin":
        st.warning("Solo admin puede ver historial")
    else:
        st.dataframe(cargar_historial_dataframe())

# =========================
# PEDIDOS
# =========================
elif menu == "Solicitar Pedidos":
    df = cargar_inventario_dataframe()
    bajos = df[df["CANTIDAD_ACTUAL"].astype(int) <= 1]
    st.dataframe(bajos)

# =========================
# LOG ADMIN
# =========================
if st.session_state["rol"] == "admin":
    st.subheader("📊 Actividad del sistema")
    st.dataframe(st.session_state["log"])