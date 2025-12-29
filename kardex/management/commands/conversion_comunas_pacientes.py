import pandas as pd

# Rutas
archivo_origen = "C:\\Users\\Informatica\\Desktop\\some2025\\db_some\\db_some_excel_maestra.xlsx"
archivo_salida = "C:\\Users\\Informatica\\Desktop\\some2025\\db_some\\db_some_excel_maestra_actualizado.xlsx"

# 1. Leer la hoja de comunas (columnas A y F)
df_comunas = pd.read_excel(archivo_origen, sheet_name="comunas_locas", header=None, usecols="A,F")
df_comunas.columns = ["id", "codigo"]

# 2. Leer la hoja de pacientes
df_pacientes = pd.read_excel(archivo_origen, sheet_name="pacientes_locos")

# 3. Verificar columna comuna_id
if "comuna_id" not in df_pacientes.columns:
    raise ValueError("La columna 'comuna_id' no fue encontrada en pacientes_locos")

# 4. Crear el mapeo de código a ID
codigo_a_id = dict(zip(df_comunas["codigo"], df_comunas["id"]))

# 5. Reemplazar los códigos por IDs en comuna_id
df_pacientes["comuna_id"] = df_pacientes["comuna_id"].map(codigo_a_id)

# 6. Guardar resultado en nuevo archivo Excel (solo esta hoja por ahora)
with pd.ExcelWriter(archivo_salida, engine="openpyxl", mode="w") as writer:
    df_pacientes.to_excel(writer, sheet_name="pacientes_locos", index=False)

print("✅ Archivo actualizado guardado como:", archivo_salida)
