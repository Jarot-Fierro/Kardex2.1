function cargarDatosFicha(fichaId) {
    function setSelectValue(selector, value, label) {
        if (value === null || value === undefined || value === '') return;
        const $el = $(selector);
        if ($el.length === 0) return;
        const valStr = String(value);
        // Si no existe la opción, agregarla (compatible con select2)
        if ($el.find(`option[value="${valStr}"]`).length === 0) {
            const text = (label !== undefined && label !== null && label !== '') ? String(label) : valStr;
            const newOpt = new Option(text, valStr, true, true);
            $el.append(newOpt);
        }
        $el.val(valStr).trigger('change');
    }

    $.ajax({
        url: `/api/ingreso-paciente-ficha/${fichaId}/`,  // Ajusta si tu ruta es otra
        method: 'GET',
        success: function (data) {
            // **Corrección aquí**: paciente = data.paciente (no data.paciente.paciente)
            const paciente = data.paciente || {};
            // Establecer modo edición y IDs ocultos cuando viene desde API
            if (paciente && paciente.id) {
                $('#paciente_id_hidden').val(paciente.id).trigger('change');
                $('#form_action_hidden').val('edit');
            } else {
                $('#paciente_id_hidden').val('').trigger('change');
            }

            // Botones
            const caratulaUrl = `/kardex/pdfs/ficha/${data.id}/`;
            const stickersUrl = `/kardex/pdfs/stickers/ficha/${data.id}/`;
            $('#btn-caratula')
                .removeClass('disabled')
                .attr('aria-disabled', 'false')
                .attr('href', caratulaUrl);
            $('#btn-stickers')
                .removeClass('disabled')
                .attr('aria-disabled', 'false')
                .attr('href', stickersUrl);

            // Botón Pasivar/Despasivar: siempre apunta a la última ficha cargada
            const $btnPasivar = $('#btn-pasivar');
            if ($btnPasivar.length) {
                const toggleUrl = `/kardex/fichas/${data.id}/toggle-pasivar/`;
                $btnPasivar
                    .removeClass('disabled')
                    .attr('aria-disabled', 'false')
                    .attr('href', toggleUrl)
                    .text(data.pasivado ? 'Despasivar' : 'Pasivar');
                // Ajustar estilo según estado
                $btnPasivar.toggleClass('btn-outline-danger', !!data.pasivado);
                $btnPasivar.toggleClass('btn-outline-warning', !data.pasivado);
            }

            // Botón Pasivar/Despasivar en sección Gestión
            const $btnPasivarGestion = $('#btn-pasivar-gestion');
            if ($btnPasivarGestion.length) {
                const toggleUrl = `/kardex/fichas/${data.id}/toggle-pasivar/`;
                $btnPasivarGestion
                    .removeClass('disabled')
                    .attr('aria-disabled', 'false')
                    .attr('href', toggleUrl)
                    .text(data.pasivado ? 'Despasivar' : 'Pasivar');
                $btnPasivarGestion.toggleClass('btn-info', !!data.pasivado);
                $btnPasivarGestion.toggleClass('btn-info', !data.pasivado);
            }

            // --- Sincronizar los campos select2 / selects ---
            // Ficha
            const fichaOption = new Option(data.numero_ficha_sistema || data.numero_ficha || data.id, data.id, true, true);
            $('#id_ficha').append(fichaOption).trigger('change');
            // Hidden ficha id y modo
            $('#ficha_id_hidden').val(data.id || '').trigger('change');
            $('#form_action_hidden').val('edit');

            // RUT
            if (paciente.rut) {
                const $rutCtrl = $('#id_rut');
                if ($rutCtrl.is('input')) {
                    $rutCtrl.val(paciente.rut).trigger('change');
                } else {
                    const rutOption = new Option(paciente.rut, paciente.rut, true, true);
                    $rutCtrl.append(rutOption).trigger('change');
                }
            }

            // Código (si aplica)
            if (paciente.codigo) {
                const codigoOption = new Option(paciente.codigo, paciente.codigo, true, true);
                $('#id_codigo').append(codigoOption).trigger('change');
            }

            // Campos de texto / input
            $('#nombre_paciente').val(paciente.nombre || '');
            $('#apellido_paterno_paciente').val(paciente.apellido_paterno || '');
            $('#apellido_materno_paciente').val(paciente.apellido_materno || '');
            $('#id_rut_madre').val(paciente.rut_madre || '');
            setSelectValue('#sexo_paciente', paciente.sexo);
            setSelectValue('#estado_civil_paciente', paciente.estado_civil);
            $('#nombres_padre_paciente').val(paciente.nombres_padre || '');
            $('#nombres_madre_paciente').val(paciente.nombres_madre || '');
            $('#nombre_pareja_paciente').val(paciente.nombre_pareja || '');
            $('#direccion_paciente').val(paciente.direccion || '');
            $('#telefono_personal').val(paciente.numero_telefono1 || '');
            $('#numero_telefono2_paciente').val(paciente.numero_telefono2 || '');
            $('#pasaporte_paciente').val(paciente.pasaporte || '');
            $('#nip_paciente').val(paciente.nip || paciente.nip || '');
            $('#rut_responsable_temporal_paciente').val(paciente.rut_responsable_temporal || '');
            $('#alergico_a').val(paciente.alergico_a || '');

            $('#usar_rut_madre_como_responsable_paciente')
                .prop('checked', !!paciente.usar_rut_madre_como_responsable)
                .trigger('change');
            $('#recien_nacido_paciente')
                .prop('checked', !!paciente.recien_nacido)
                .trigger('change');
            $('#extranjero_paciente')
                .prop('checked', !!paciente.extranjero)
                .trigger('change');
            $('#fallecido_paciente')
                .prop('checked', !!paciente.fallecido)
                .trigger('change');
            // Sin teléfono: reflejar estado desde la API y disparar change para reglas
            if (typeof paciente.sin_telefono !== 'undefined') {
                $('#sin_telefono_paciente')
                    .prop('checked', !!paciente.sin_telefono)
                    .trigger('change');
            }

            // Fecha de fallecimiento si existe
            if (paciente.fecha_fallecimiento) {
                const isoFal = String(paciente.fecha_fallecimiento);
                const datePart = isoFal.split('T')[0];
                const partsFal = datePart.split('-');
                if (partsFal.length === 3) {
                    const [y, m, d] = partsFal;
                    $('#fecha_fallecimiento_paciente').val(`${d}/${m}/${y}`).trigger('change');
                } else {
                    $('#fecha_fallecimiento_paciente').val(paciente.fecha_fallecimiento).trigger('change');
                }
            } else {
                $('#fecha_fallecimiento_paciente').val('').trigger('change');
            }

            // Otros campos
            $('#ocupacion_paciente').val(paciente.ocupacion || '');
            $('#representante_legal_paciente').val(paciente.representante_legal || '');
            $('#nombre_social_paciente').val(paciente.nombre_social || '');

            setSelectValue('#comuna_paciente', paciente.comuna);
            setSelectValue('#prevision_paciente', paciente.prevision);
            setSelectValue('#usuario_paciente', paciente.usuario);
            setSelectValue('#genero_paciente', paciente.genero);

            // Fecha de nacimiento
            if (paciente.fecha_nacimiento) {
                const iso = String(paciente.fecha_nacimiento);
                const datePart = iso.split('T')[0];
                const parts = datePart.split('-');
                if (parts.length === 3) {
                    const [year, month, day] = parts;
                    const ddmmyyyy = `${day}/${month}/${year}`;
                    $('#fecha_nacimiento_paciente').val(ddmmyyyy).trigger('change');
                    $('#id_fecha_nacimiento').val(ddmmyyyy).trigger('change');
                }
            }

            // Fechas de la ficha (created / updated)
            if (data.created_at) {
                const [year, month, day] = data.created_at.split("T")[0].split("-");
                $('#ficha_created_at_text').text(`${day}/${month}/${year}`);
            } else {
                $('#ficha_created_at_text').text('-');
            }

            if (data.updated_at) {
                const [year, month, day] = data.updated_at.split("T")[0].split("-");
                $('#ficha_updated_at_text').text(`${day}/${month}/${year}`);
            } else {
                $('#ficha_updated_at_text').text('-');
            }

            // Aplicar reglas de negocio si existen
            if (window._pacienteApplyRules) {
                try {
                    window._pacienteApplyRules();
                } catch (err) {
                    console.error('Error en _pacienteApplyRules:', err);
                }
            }
        },
        error: function (xhr, status, error) {
            console.error('Error cargar datos ficha:', status, error, xhr.responseText);
            alert('Error al cargar los datos de la ficha.');
        }
    });
}

// Exponer globalmente
window.cargarDatosFicha = cargarDatosFicha;

// Función para vaciar el formulario de paciente (excepto el campo RUT)
window.resetPacienteForm = function () {
    try {
        const $form = $('form');
        if (!$form.length) return;

        const $rut = $('#id_rut');
        const rutVal = $rut.val();

        // Limpiar inputs de texto/fecha/número/email, excepto RUT
        $form.find('input').each(function () {
            const $el = $(this);
            const type = ($el.attr('type') || '').toLowerCase();
            const id = $el.attr('id') || '';
            if (id === 'id_rut') return; // conservar RUT ingresado
            if (['hidden'].includes(type)) return; // hiddens se controlan abajo
            if (['checkbox', 'radio'].includes(type)) {
                $el.prop('checked', false).trigger('change');
                return;
            }
            // text, number, date, email, tel, etc.
            $el.val('').trigger('change');
        });

        // Limpiar textareas
        $form.find('textarea').val('').trigger('change');

        // Limpiar selects y select2
        $form.find('select').each(function () {
            const $sel = $(this);
            const id = $sel.attr('id') || '';
            if (id === 'id_rut') return; // no tocar selector de RUT si fuera select2
            $sel.val(null).trigger('change');
            // Remover opciones dinámicas para evitar residuos (sin afectar catálogos cargados por AJAX)
            if ($sel.hasClass('select2-hidden-accessible')) {
                // mantener placeholder, remover selección actual
            }
        });

        // Reset de campos ocultos y modo
        $('#paciente_id_hidden').val('').trigger('change');
        $('#ficha_id_hidden').val('').trigger('change');
        $('#form_action_hidden').val('add');

        // Deshabilitar botones relacionados a una ficha cargada
        $('#btn-caratula, #btn-stickers').addClass('disabled').attr('aria-disabled', 'true').attr('href', '#');
        const $btnPasivar = $('#btn-pasivar, #btn-pasivar-gestion');
        $btnPasivar.addClass('disabled').attr('aria-disabled', 'true').attr('href', '#').text('Pasivar')
            .removeClass('btn-outline-info btn-info').addClass('btn-outline-warning');

        // Limpiar labels de fechas
        $('#ficha_created_at_text').text('-');
        $('#ficha_updated_at_text').text('-');

        // Restaurar el valor del RUT en caso de que algún trigger lo haya afectado
        if (rutVal !== undefined) {
            $rut.val(rutVal);
        }
    } catch (e) {
        console.warn('resetPacienteForm fallo:', e);
    }
};

$('#id_ficha, #id_rut, #id_codigo').on('select2:select', function (e) {
    const fichaId = e.params.data.id;
    cargarDatosFicha(fichaId);
});
