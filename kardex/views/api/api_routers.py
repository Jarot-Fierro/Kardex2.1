from rest_framework import routers

from kardex.views.api.catalogos import ServicioClinicoViewSet, ProfesionalViewSet
from kardex.views.api.comunas import ComunaViewSet
from kardex.views.api.fichas import FichaViewSet
from kardex.views.api.movimiento_fichas_update import FichaPacienteViewSet
from kardex.views.api.pacientes import PacienteViewSet
from kardex.views.api.prevision import PrevisionViewSet
from kardex.views.api.recepcion_ficha import RecepcionFichaViewSet
from kardex.views.api.sector import SectorViewSet
from kardex.views.api.traspasos import TraspasoFichaViewSet

router = routers.DefaultRouter()
router.register(r'ingreso-paciente-ficha', FichaViewSet, basename='ficha')
router.register(r'recepcion-ficha', RecepcionFichaViewSet, basename='recepcion-ficha')
router.register(r'traspaso-ficha', TraspasoFichaViewSet, basename='traspaso-ficha')
router.register(r'pacientes', PacienteViewSet, basename='paciente')
router.register(r'servicios-clinicos', ServicioClinicoViewSet, basename='servicio-clinico')
router.register(r'profesionales', ProfesionalViewSet, basename='profesional')
router.register(r"comunas", ComunaViewSet)
router.register(r"prevision", PrevisionViewSet)
router.register(r"sector", SectorViewSet)

router.register(r'fichas', FichaPacienteViewSet, basename='ficha-paciente')
