# --------VER INVENTARIO (EDITABLE Y ELIMINABLE)--------
elif menu == "Ver Inventario": 
    st.subheader("Reporte General de Inventario") 
    st.caption("💡 Puedes corregir, agregar o eliminar productos directamente.")

    inventario = cargar_inventario() 
    
    if not inventario: 
        st.info("No hay productos.") 
    else: 
        lista = [] 
        for nombre, datos in inventario.items(): 
            movimientos = datos.get("movimientos", [])
            ult = movimientos[-1]["fecha"] if movimientos else "-"
            
            lista.append({ 
                "Producto Original": nombre,
                "PRODUCTO": nombre, 
                "CANTIDAD": limpiar_entero(datos.get("cantidad", 0)), 
                "ALMACÉN": limpiar_entero(datos.get("almacen", 1)) or 1,
                "ULTIMO MOVIMIENTO": ult 
            }) 
        
        # 🔥 TABLA EDITABLE + ELIMINABLE
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
            num_rows="dynamic"  # 👈 PERMITE ELIMINAR FILAS
        )

        # 🔥 GUARDADO CON SOPORTE PARA ELIMINAR
        if tabla != lista:
            nuevo = {}
            nombres = set()
            error = False

            for fila in tabla:
                nuevo_nombre = fila["PRODUCTO"].strip().upper()
                original = fila["Producto Original"]

                if not nuevo_nombre:
                    st.error("❌ Nombre vacío no permitido")
                    error = True
                    break

                if nuevo_nombre in nombres:
                    st.error(f"❌ Producto duplicado: {nuevo_nombre}")
                    error = True
                    break

                nombres.add(nuevo_nombre)

            if not error:
                for fila in tabla:
                    original = fila["Producto Original"]
                    nuevo_nombre = fila["PRODUCTO"].strip().upper()

                    # 👇 SOLO GUARDA LOS QUE QUEDAN (los borrados desaparecen)
                    if original in inventario:
                        nuevo[nuevo_nombre] = inventario[original]
                        nuevo[nuevo_nombre]["almacen"] = fila["ALMACÉN"] or 1
                    else:
                        # 👇 SI AGREGAS UNA FILA NUEVA
                        nuevo[nuevo_nombre] = {
                            "cantidad": 0,
                            "almacen": fila["ALMACÉN"] or 1,
                            "fecha_ingreso": datetime.now().strftime('%Y-%m-%d'),
                            "movimientos": []
                        }

                guardar_inventario(nuevo)
                st.success("✅ Inventario actualizado (incluye eliminaciones)")
                st.rerun()

        st.download_button("Descargar PDF", exportar_pdf(), "reporte_inventario.pdf")