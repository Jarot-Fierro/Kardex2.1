import sys

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import transaction, DatabaseError
from tqdm import tqdm

from clinica.models import MovimientoFicha, Ficha, MovimientoMonologoControlado
from establecimientos.models.establecimiento import Establecimiento
from establecimientos.models.sectores import Sector
from establecimientos.models.servicio_clinico import ServicioClinico
from personas.models.pacientes import Paciente
from personas.models.profesionales import Profesional
from personas.models.usuario_anterior import UsuarioAnterior
from users.models import User, Role


class Command(BaseCommand):
    help = "Limpia datos excepto establecimiento id_establecimiento"

    def chunked_update(self, queryset, chunk_size=2000, **kwargs):
        """Actualiza un queryset en lotes para mostrar progreso."""
        total = queryset.count()
        if total == 0:
            return 0
        
        pbar = tqdm(total=total, desc="Actualizando", unit="reg", leave=False)
        updated_total = 0
        
        # Obtenemos los IDs para iterar de forma estable
        ids = list(queryset.values_list('pk', flat=True))
        
        for i in range(0, len(ids), chunk_size):
            chunk_ids = ids[i:i + chunk_size]
            updated = queryset.model.objects.filter(pk__in=chunk_ids).update(**kwargs)
            updated_total += updated
            pbar.update(len(chunk_ids))
        
        pbar.close()
        return updated_total

    def chunked_delete(self, queryset, chunk_size=2000):
        """Elimina un queryset en lotes para mostrar progreso."""
        total = queryset.count()
        if total == 0:
            return 0
        
        pbar = tqdm(total=total, desc="Eliminando", unit="reg", leave=False)
        deleted_total = 0
        
        # Para eliminar, es mejor iterar mientras existan registros si el filtro es sobre el mismo queryset
        # Pero para ser genéricos con el exclude, usaremos IDs
        ids = list(queryset.values_list('pk', flat=True))
        
        for i in range(0, len(ids), chunk_size):
            chunk_ids = ids[i:i + chunk_size]
            deleted = queryset.model.objects.filter(pk__in=chunk_ids).delete()[0]
            deleted_total += deleted
            pbar.update(len(chunk_ids))
        
        pbar.close()
        return deleted_total

    def handle(self, *args, **kwargs):
        id_establecimiento = 1
        self.stdout.write(self.style.MIGRATE_HEADING(f"Iniciando limpieza para el establecimiento ID: {id_establecimiento}"))

        try:
            with transaction.atomic():
                # =========================
                # 0. ROLES
                # =========================
                self.stdout.write("\n1. Actualizando roles (establecimiento -> None)...")
                qs_roles = Role.objects.exclude(establecimiento_id=id_establecimiento)
                roles_count = self.chunked_update(qs_roles, establecimiento=None)
                self.stdout.write(self.style.SUCCESS(f" OK ({roles_count} roles actualizados)"))

                # =========================
                # 1. DELETE PRINCIPAL (Movimientos e infraestructura)
                # =========================
                self.stdout.write("\n2. Eliminando movimientos e infraestructura...")
                
                # Movimientos Monólogo
                qs_monologo = MovimientoMonologoControlado.objects.exclude(establecimiento_id=id_establecimiento)
                m_monologo = self.chunked_delete(qs_monologo)
                
                # Movimientos Ficha
                qs_m_ficha = MovimientoFicha.objects.exclude(establecimiento_id=id_establecimiento)
                m_ficha = self.chunked_delete(qs_m_ficha)
                
                # Fichas
                qs_fichas = Ficha.objects.exclude(establecimiento_id=id_establecimiento)
                fichas = self.chunked_delete(qs_fichas)
                
                # Sectores
                qs_sectores = Sector.objects.exclude(establecimiento_id=id_establecimiento)
                sectores = self.chunked_delete(qs_sectores)
                
                # Servicios
                qs_servicios = ServicioClinico.objects.exclude(establecimiento_id=id_establecimiento)
                servicios = self.chunked_delete(qs_servicios)
                
                # Profesionales
                qs_profesionales = Profesional.objects.exclude(establecimiento_id=id_establecimiento)
                profesionales = self.chunked_delete(qs_profesionales)

                self.stdout.write(self.style.SUCCESS(" OK"))
                self.stdout.write(f"   - Movimientos: {m_monologo + m_ficha}")
                self.stdout.write(f"   - Fichas: {fichas}")
                self.stdout.write(f"   - Sectores/Servicios: {sectores + servicios}")
                self.stdout.write(f"   - Profesionales: {profesionales}")

                # =========================
                # 2. LIMPIAR RELACIONES (No borrar registros, solo desvincular)
                # =========================
                self.stdout.write("\n3. Limpiando relaciones (Pacientes, Fichas, UsuariosAnterior)...")
                
                # Pacientes
                qs_pac_upd = Paciente.objects.exclude(usuario_anterior__establecimiento_id=id_establecimiento)
                pacientes_upd = self.chunked_update(qs_pac_upd, usuario_anterior=None)
                
                # Fichas (desvincular usuario anterior)
                qs_fich_upd = Ficha.objects.exclude(usuario_anterior__establecimiento_id=id_establecimiento)
                fichas_upd = self.chunked_update(qs_fich_upd, usuario_anterior=None)

                # UsuariosAnterior
                qs_uant_upd = UsuarioAnterior.objects.exclude(establecimiento_id=id_establecimiento)
                u_ant_upd = self.chunked_update(qs_uant_upd, establecimiento=None)
                
                self.stdout.write(self.style.SUCCESS(f" OK"))
                self.stdout.write(f"   - Pacientes desvinculados: {pacientes_upd}")
                self.stdout.write(f"   - Fichas desvinculadas: {fichas_upd}")
                self.stdout.write(f"   - UsuariosAnterior desvinculados: {u_ant_upd}")

                # =========================
                # 3. USERS
                # =========================
                self.stdout.write("\n4. Procesando usuarios...")
                
                users_to_unassign = User.objects.exclude(establecimiento_id=id_establecimiento)
                u_count = users_to_unassign.count()

                if u_count > 0:
                    # Limpiar referencias de auditoría
                    self.chunked_update(Paciente.objects.filter(created_by__in=users_to_unassign), created_by=None)
                    self.chunked_update(Paciente.objects.filter(updated_by__in=users_to_unassign), updated_by=None)
                    self.chunked_update(Profesional.objects.filter(created_by__in=users_to_unassign), created_by=None)
                    self.chunked_update(Profesional.objects.filter(updated_by__in=users_to_unassign), updated_by=None)

                    # Desvincular usuarios
                    self.chunked_update(users_to_unassign, establecimiento=None, rol=None)
                
                self.stdout.write(self.style.SUCCESS(f" OK (Usuarios desvinculados: {u_count})"))

                # =========================
                # 4. HISTÓRICOS
                # =========================
                self.stdout.write("\n5. Limpiando registros históricos de simple-history...")
                h_count = 0
                
                # Lista de modelos con historia
                history_models = []
                for model in apps.get_models():
                    if hasattr(model, 'history'):
                        history_model = model.history.model
                        if hasattr(history_model, 'history_user'):
                            history_models.append(history_model)

                if history_models and u_count > 0:
                    pbar_hist = tqdm(history_models, desc="Procesando modelos históricos", unit="modelo")
                    for history_model in pbar_hist:
                        upd = history_model.objects.filter(
                            history_user__in=users_to_unassign
                        ).update(history_user=None)
                        h_count += upd
                    pbar_hist.close()

                self.stdout.write(self.style.SUCCESS(f" OK ({h_count} registros históricos actualizados)"))

                # =========================
                # 5. ELIMINACIÓN FINAL (Solo establecimientos ajenos)
                # =========================
                self.stdout.write("\n6. Ejecutando eliminación final de establecimientos...")
                qs_est_del = Establecimiento.objects.exclude(id=id_establecimiento)
                e_deleted = self.chunked_delete(qs_est_del)
                self.stdout.write(self.style.SUCCESS(f" OK (Establecimientos borrados: {e_deleted})"))

        except DatabaseError as e:
            self.stdout.write(self.style.ERROR(f"\n❌ ERROR DE BASE DE DATOS: {str(e)}"))
            self.stdout.write(self.style.WARNING("La transacción ha sido revertida automáticamente."))
            sys.exit(1)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ ERROR INESPERADO: {str(e)}"))
            self.stdout.write(self.style.WARNING("Error detectado. Deteniendo ejecución para proteger la integridad de los datos."))
            sys.exit(1)

        self.stdout.write(self.style.SUCCESS('\n✔ LIMPIEZA COMPLETADA EXITOSAMENTE'))