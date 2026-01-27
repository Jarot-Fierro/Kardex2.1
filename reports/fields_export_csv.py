fields_paciente_csv = [
    # StandardModel
    'id',
    'created_at',
    'updated_at',
    'status',

    # IDENTIFICACIÓN
    'codigo',
    'rut',
    'nip',
    'nombre',
    'apellido_paterno',
    'apellido_materno',
    'nombre_social',
    'rut_madre',
    'rut_responsable_temporal',
    'usar_rut_madre_como_responsable',
    'pasaporte',
    'pueblo_indigena',
    'genero',
    'sexo',
    'estado_civil',

    # DATOS DE NACIMIENTO
    'fecha_nacimiento',

    # DATOS FAMILIARES
    'nombres_padre',
    'nombres_madre',
    'nombre_pareja',
    'representante_legal',

    # CONTACTO Y DIRECCIÓN
    'direccion',
    'sin_telefono',
    'numero_telefono1',
    'numero_telefono2',
    'ocupacion',

    # ESTADO DEL PACIENTE
    'recien_nacido',
    'extranjero',
    'fallecido',
    'fecha_fallecimiento',
    'alergico_a',

    # RELACIONES
    'comuna__nombre',
    'prevision__nombre',
    'usuario__username',
    'usuario_anterior__rut',
]

fields_ficha_csv = [
    # === CAMPOS HEREDADOS (StandardModel) ===
    'id',
    'created_at',
    'updated_at',
    'status',

    # === CAMPOS PRINCIPALES DE FICHA ===
    'numero_ficha_sistema',
    'numero_ficha_tarjeta',
    'pasivado',
    'observacion',

    # === RELACIONES ===
    'usuario__username',
    'paciente__rut',
    'paciente__nombre',
    'paciente__apellido_paterno',
    'paciente__apellido_materno',
    'paciente__codigo',
    'establecimiento__nombre',
    'sector__color',
]

fields_movimiento_ficha_csv = [
    # === CAMPOS HEREDADOS (StandardModel) ===
    'id',
    'created_at',
    'updated_at',
    'status',

    # === FECHAS DE MOVIMIENTO ===
    'fecha_envio',
    'fecha_recepcion',
    'fecha_traspaso',

    # === OBSERVACIONES ===
    'observacion_envio',
    'observacion_recepcion',
    'observacion_traspaso',

    # === ESTADOS ===
    'estado_envio',
    'estado_recepcion',
    'estado_traspaso',

    # === SERVICIOS CLÍNICOS ===
    'servicio_clinico_envio__nombre',
    'servicio_clinico_recepcion__nombre',
    'servicio_clinico_traspaso__nombre',

    # === USUARIOS ===
    'usuario_envio__username',
    'usuario_recepcion__username',
    'usuario_traspaso__username',

    # === USUARIOS ANTERIORES ===
    'usuario_envio_anterior__rut',
    'usuario_recepcion_anterior__rut',

    # === PROFESIONALES ===
    'profesional_envio__rut',
    'profesional_envio__nombres',
    'profesional_recepcion__rut',
    'profesional_recepcion__nombres',
    'profesional_traspaso__rut',
    'profesional_traspaso__nombres',

    # === ESTABLECIMIENTO ===
    'establecimiento__nombre',

    # === RUTS ANTERIORES ===
    'rut_anterior',
    'rut_anterior_profesional',

    # === FICHA RELACIONADA ===
    'ficha__numero_ficha_sistema',
    'ficha__numero_ficha_tarjeta',
    'ficha__paciente__rut',
    'ficha__paciente__nombre',
    'ficha__paciente__apellido_paterno',
    'ficha__paciente__apellido_materno',
]
