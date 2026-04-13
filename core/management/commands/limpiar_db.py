import sys

from django.apps import apps
from django.contrib.admin.models import LogEntry
from django.core.management.base import BaseCommand
from django.db import transaction, DatabaseError

from clinica.models import MovimientoFicha, Ficha, MovimientoMonologoControlado
from establecimientos.models import Establecimiento
from establecimientos.models.sectores import Sector
from establecimientos.models.servicio_clinico import ServicioClinico
from personas.models.pacientes import Paciente
from personas.models.profesionales import Profesional
from personas.models.usuario_anterior import UsuarioAnterior
from users.models import User, Role


class Command(BaseCommand):
    help = "Limpia datos excepto establecimiento id_establecimiento"

    def handle(self, *args, **kwargs):
        id_establecimiento = 5
        self.stdout.write(self.style.MIGRATE_HEADING(f"Iniciando limpieza para el establecimiento ID: {id_establecimiento}"))

        try:
            with transaction.atomic():
                # =========================
                # 0. ROLES (NUEVA SOLICITUD)
                # =========================
                self.stdout.write("Actualizando roles (establecimiento -> None)...", ending="")
                roles_count = Role.objects.all().update(establecimiento=None)
                self.stdout.write(self.style.SUCCESS(f" OK ({roles_count} actualizados)"))

                # =========================
                # 1. DELETE PRINCIPAL
                # =========================
                self.stdout.write("Eliminando movimientos e infraestructura...", ending="")
                m_monologo = MovimientoMonologoControlado.objects.exclude(establecimiento_id=id_establecimiento).delete()[0]
                m_ficha = MovimientoFicha.objects.exclude(establecimiento_id=id_establecimiento).delete()[0]
                fichas = Ficha.objects.exclude(establecimiento_id=id_establecimiento).delete()[0]
                sectores = Sector.objects.exclude(establecimiento_id=id_establecimiento).delete()[0]
                servicios = ServicioClinico.objects.exclude(establecimiento_id=id_establecimiento).delete()[0]
                profesionales = Profesional.objects.exclude(establecimiento_id=id_establecimiento).delete()[0]
                self.stdout.write(self.style.SUCCESS(" OK"))
                self.stdout.write(f"   - Movimientos: {m_monologo + m_ficha}")
                self.stdout.write(f"   - Fichas: {fichas}")
                self.stdout.write(f"   - Sectores/Servicios: {sectores + servicios}")
                self.stdout.write(f"   - Profesionales: {profesionales}")

                # =========================
                # 2. LIMPIAR FK
                # =========================
                self.stdout.write("Limpiando claves foráneas (Pacientes y UsuarioAnterior)...", ending="")
                pacientes_upd = Paciente.objects.exclude(
                    usuario_anterior__establecimiento_id=id_establecimiento
                ).update(usuario_anterior=None)
                u_ant_del = UsuarioAnterior.objects.exclude(establecimiento_id=id_establecimiento).delete()[0]
                self.stdout.write(self.style.SUCCESS(f" OK (Pacientes actualizados: {pacientes_upd}, UsuariosAnterior borrados: {u_ant_del})"))

                # =========================
                # 3. USERS
                # =========================
                self.stdout.write("Procesando usuarios a eliminar...", ending="")
                users_to_delete = User.objects.exclude(establecimiento_id=id_establecimiento)
                u_count = users_to_delete.count()

                # limpiar relaciones
                Paciente.objects.filter(created_by__in=users_to_delete).update(created_by=None)
                Paciente.objects.filter(updated_by__in=users_to_delete).update(updated_by=None)
                Profesional.objects.filter(created_by__in=users_to_delete).update(created_by=None)
                Profesional.objects.filter(updated_by__in=users_to_delete).update(updated_by=None)

                # logs admin
                LogEntry.objects.filter(user__in=users_to_delete).delete()
                self.stdout.write(self.style.SUCCESS(f" OK (Usuarios identificados: {u_count})"))

                # =========================
                # 4. HISTÓRICOS
                # =========================
                self.stdout.write("Limpiando registros históricos de simple-history...", ending="")
                h_count = 0
                for model in apps.get_models():
                    if hasattr(model, 'history'):
                        history_model = model.history.model
                        if hasattr(history_model, 'history_user'):
                            upd = history_model.objects.filter(
                                history_user__in=users_to_delete
                            ).update(history_user=None)
                            h_count += upd
                self.stdout.write(self.style.SUCCESS(f" OK ({h_count} registros históricos actualizados)"))

                # =========================
                # 5. ELIMINACIÓN FINAL
                # =========================
                self.stdout.write("Ejecutando eliminación final de usuarios y establecimientos...", ending="")
                u_deleted = users_to_delete.delete()[0]
                e_deleted = Establecimiento.objects.exclude(id=id_establecimiento).delete()[0]
                self.stdout.write(self.style.SUCCESS(f" OK (Usuarios: {u_deleted}, Establecimientos: {e_deleted})"))

        except DatabaseError as e:
            self.stdout.write(self.style.ERROR(f"\n❌ ERROR DE BASE DE DATOS: {str(e)}"))
            self.stdout.write(self.style.WARNING("La transacción ha sido revertida automáticamente."))
            sys.exit(1)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ ERROR INESPERADO: {str(e)}"))
            # Obtenemos el nombre de la sección aproximada mediante el flujo
            self.stdout.write(self.style.WARNING("Error detectado. Deteniendo ejecución para proteger la integridad de los datos."))
            sys.exit(1)

        self.stdout.write(self.style.SUCCESS('\n✔ LIMPIEZA COMPLETADA EXITOSAMENTE'))