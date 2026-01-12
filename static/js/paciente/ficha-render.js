// ficha_render.js

function cargarPaciente(data) {
    const p = data.paciente;
    if (!p) return;

    setValue('id_paciente_id', p.id);

    setValue('id_nombre', p.nombre);
    setValue('id_apellido_paterno', p.apellido_paterno);
    setValue('id_apellido_materno', p.apellido_materno);
    setValue('id_nombre_social', p.nombre_social);
    setValue('id_pasaporte', p.pasaporte);
    setValue('id_nip', p.nip);

    setValue('id_fecha_nacimiento', p.fecha_nacimiento);
    setValue('id_sexo', p.sexo);
    setValue('id_estado_civil', p.estado_civil);

    setValue('id_recien_nacido', p.recien_nacido);
    setValue('id_extranjero', p.extranjero);
    setValue('id_pueblo_indigena', p.pueblo_indigena);
    setValue('id_fallecido', p.fallecido);
    setValue('id_fecha_fallecimiento', p.fecha_fallecimiento);

    setValue('id_rut_madre', p.rut_madre);
    setValue('id_nombres_madre', p.nombres_madre);
    setValue('id_nombres_padre', p.nombres_padre);
    setValue('id_nombre_pareja', p.nombre_pareja);
    setValue('id_representante_legal', p.representante_legal);
    setValue('id_rut_responsable_temporal', p.rut_responsable_temporal);
    setValue('id_usar_rut_madre_como_responsable', p.usar_rut_madre_como_responsable);

    setValue('id_direccion', p.direccion);
    setSelect2ById('id_comuna', p.comuna_id);
    setSelect2ById('id_genero', p.genero_id);
    setSelect2ById('id_prevision', p.prevision_id);

    setValue('id_ocupacion', p.ocupacion);
    setValue('id_numero_telefono1', p.numero_telefono1);
    setValue('id_numero_telefono2', p.numero_telefono2);

    setText('id_usuario_anterior', p.usuario_anterior);
}

function cargarFicha(data) {
    if (!data.ficha) return;

    const f = data.ficha;

    setValue('id_ficha', f.numero_ficha_sistema);
    setValue('id_observacion', f.observacion);
    setSelect2ById('id_sector', f.sector_id);

    const fecha = f.fecha_creacion_anterior || f.fecha_creacion;
    setText('id_fecha_creacion', formatearFechaHora(fecha));
}

function cargaTabla(data) {
    const tbody = $('#tabla-fichas tbody');
    tbody.empty();

    if (data.ficha?.numero_ficha_sistema) {
        tbody.append(`
            <tr class="table-primary fw-bold">
                <td>${data.ficha.establecimiento ?? 'SIN ESTABLECIMIENTO'}</td>
                <td class="text-center">
                    <span class="badge bg-primary">
                        ${data.ficha.numero_ficha_sistema}
                    </span>
                </td>
            </tr>
        `);
    }

    if (Array.isArray(data.otras_fichas)) {
        data.otras_fichas.forEach(f => {
            if (f.numero_ficha_sistema === data.ficha?.numero_ficha_sistema) return;

            tbody.append(`
                <tr>
                    <td>${f.establecimiento ?? 'SIN ESTABLECIMIENTO'}</td>
                    <td class="text-center">
                        <span class="badge bg-secondary">
                            ${f.numero_ficha_sistema}
                        </span>
                    </td>
                </tr>
            `);
        });
    }
}

function cargaUbicacionFicha(data) {
    const mov = data.ficha?.movimientos?.[0];

    if (!mov) {
        setText('id_servicio_clinico', 'SIN INFORMACIÓN');
        setText('id_profesional_cargo', 'SIN INFORMACIÓN');
        setText('id_fecha_envio', '—');
        return;
    }

    setText('id_servicio_clinico', mov.destino);
    setText('id_profesional_cargo', mov.profesional_nombre);
    setText('id_fecha_envio', formatearFechaHora(mov.fecha_envio));
}
