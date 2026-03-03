import pandas as pd
from django.core.management.base import BaseCommand
from tqdm import tqdm

from personas.models.pacientes import Paciente


class Command(BaseCommand):
    help = "Actualiza recien_nacido, extranjero y fallecido según Excel (busca por RUT)"

    def add_arguments(self, parser):
        parser.add_argument("excel_path", type=str, help="Ruta del archivo Excel")
        parser.add_argument("--sheet", type=str, default=0, help="Hoja (default 0)")
        parser.add_argument("--skiprows", type=int, default=0, help="Filas a saltar")

    # ================= LIMPIEZA =================

    def limpiar_bool(self, valor):
        if pd.isna(valor) or valor in ("", None):
            return False

        valor = str(valor).strip().lower()

        if valor in ("1", "true", "t", "yes", "y", "si", "sí"):
            return True
        if valor in ("0", "false", "f", "no", "n"):
            return False

        return False

    def limpiar_texto(self, valor):
        if pd.isna(valor) or valor in ("", None):
            return None
        return str(valor).strip().upper()

    def normalizar_rut(self, rut):
        if not rut:
            return None

        # Quitar cualquier carácter que no sea número o K
        rut = "".join(c for c in str(rut) if c.isdigit() or c.upper() == "K").upper()

        if len(rut) < 2:
            return rut

        cuerpo = rut[:-1]
        dv = rut[-1]

        # Formatear cuerpo con puntos
        cuerpo_con_puntos = ""
        for i, char in enumerate(reversed(cuerpo)):
            if i > 0 and i % 3 == 0:
                cuerpo_con_puntos = "." + cuerpo_con_puntos
            cuerpo_con_puntos = char + cuerpo_con_puntos

        return f"{cuerpo_con_puntos}-{dv}"

    # ================= MAIN =================

    def handle(self, *args, **options):

        excel_path = options["excel_path"]
        sheet = options["sheet"]
        skiprows = options["skiprows"]

        self.stdout.write(self.style.SUCCESS(f"Leyendo Excel: {excel_path}"))

        df = pd.read_excel(
            excel_path,
            sheet_name=sheet,
            skiprows=skiprows,
            dtype=str
        )

        df = df.fillna("")
        df.columns = [str(col).strip() for col in df.columns]

        total = len(df)

        # Contadores
        actualizados = 0
        no_encontrados = 0
        inconsistencias_id = 0

        actualizados_rn = 0
        actualizados_ext = 0
        actualizados_fall = 0

        # Tamaño del lote para procesamiento
        BATCH_SIZE = 1000

        # Lista para acumular objetos modificados para bulk_update
        objetos_a_actualizar = []
        # Campos que pueden ser actualizados
        campos_update = ["recien_nacido", "extranjero", "fallecido", "fecha_fallecimiento"]

        with tqdm(total=total, desc="Actualizando", unit="reg") as pbar:
            # Procesar el DataFrame en trozos (chunks)
            for i in range(0, total, BATCH_SIZE):
                chunk = df.iloc[i:i + BATCH_SIZE]

                # Mapear datos del Excel por RUT para búsqueda rápida
                excel_data = {}
                ruts_a_buscar = []

                for _, row in chunk.iterrows():
                    rut_raw = self.limpiar_texto(row.get("cod_rutpac") or row.get("rut"))
                    rut = self.normalizar_rut(rut_raw)

                    if not rut:
                        pbar.update(1)
                        continue

                    excel_data[rut] = {
                        "rut_raw": rut_raw,
                        "id_anterior": row.get("id") or row.get("id_anterior"),
                        "nuevo_rn": self.limpiar_bool(row.get("recien_nacido") or row.get("RN")),
                        "nuevo_ext": self.limpiar_bool(row.get("extranjero")),
                        "nuevo_fall": self.limpiar_bool(row.get("fallecido")),
                        "nueva_fecha_fall": row.get("fecha_fallecido")
                    }
                    ruts_a_buscar.append(rut)
                    # También agregar el original por si acaso
                    if rut_raw and rut_raw != rut:
                        ruts_a_buscar.append(rut_raw)

                # Buscar todos los pacientes del lote en una sola query
                pacientes_db = Paciente.objects.filter(rut__in=ruts_a_buscar)
                # Crear diccionario de pacientes encontrados {rut: objeto_paciente}
                # Priorizar RUT normalizado si hay duplicados en la búsqueda por alguna razón
                pacientes_dict = {p.rut: p for p in pacientes_db}

                # Procesar cada registro del Excel en el lote
                for rut_excel, data in excel_data.items():
                    # Buscar en el diccionario de la DB
                    paciente = pacientes_dict.get(rut_excel)
                    if not paciente and data["rut_raw"]:
                        paciente = pacientes_dict.get(data["rut_raw"])

                    if not paciente:
                        no_encontrados += 1
                        pbar.update(1)
                        continue

                    # Validar ID anterior
                    id_excel = data["id_anterior"]
                    if id_excel:
                        if str(paciente.id_anterior) != str(id_excel).strip():
                            inconsistencias_id += 1
                            pbar.update(1)
                            continue

                    # Verificar cambios
                    modificado = False

                    if paciente.recien_nacido != data["nuevo_rn"]:
                        paciente.recien_nacido = data["nuevo_rn"]
                        actualizados_rn += 1
                        modificado = True

                    if paciente.extranjero != data["nuevo_ext"]:
                        paciente.extranjero = data["nuevo_ext"]
                        actualizados_ext += 1
                        modificado = True

                    if paciente.fallecido != data["nuevo_fall"]:
                        paciente.fallecido = data["nuevo_fall"]
                        actualizados_fall += 1
                        modificado = True

                    if data["nuevo_fall"] and data["nueva_fecha_fall"]:
                        try:
                            fecha_f = pd.to_datetime(data["nueva_fecha_fall"]).date()
                            if paciente.fecha_fallecimiento != fecha_f:
                                paciente.fecha_fallecimiento = fecha_f
                                modificado = True
                        except:
                            pass

                    if modificado:
                        objetos_a_actualizar.append(paciente)
                        actualizados += 1

                        # Si acumulamos muchos objetos, hacemos un bulk_update parcial para no saturar la memoria
                        if len(objetos_a_actualizar) >= BATCH_SIZE:
                            Paciente.objects.bulk_update(objetos_a_actualizar, campos_update)
                            objetos_a_actualizar = []

                    pbar.update(1)

            # Guardar remanentes
            if objetos_a_actualizar:
                Paciente.objects.bulk_update(objetos_a_actualizar, campos_update)

        # ================= RESUMEN =================

        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS("RESUMEN FINAL"))
        self.stdout.write(self.style.SUCCESS(f"Total registros Excel: {total:,}"))
        self.stdout.write(self.style.SUCCESS(f"Pacientes actualizados (al menos 1 campo): {actualizados:,}"))
        self.stdout.write(self.style.SUCCESS(f"Actualizados recien_nacido: {actualizados_rn:,}"))
        self.stdout.write(self.style.SUCCESS(f"Actualizados extranjero: {actualizados_ext:,}"))
        self.stdout.write(self.style.SUCCESS(f"Actualizados fallecido: {actualizados_fall:,}"))
        self.stdout.write(self.style.WARNING(f"No encontrados por RUT: {no_encontrados:,}"))
        self.stdout.write(self.style.WARNING(f"Inconsistencias ID anterior: {inconsistencias_id:,}"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
