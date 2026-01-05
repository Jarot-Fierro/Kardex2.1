
$(document).ready(function () {
    const $rutField = $('#id_rut');
    if ($rutField.length === 0) return;

    let lastRut = null;

    function normalizeRut(rut) {
        return String(rut || '').trim().toUpperCase();
    }

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    }

    function crearFichaAutomaticamente(rut, createUrl) {
        const url = createUrl || '/api/ingreso-paciente-ficha/auto-create/';
        const csrftoken = getCookie('csrftoken');
        return $.ajax({
            url: url,
            type: 'POST',
            dataType: 'json',
            headers: csrftoken ? { 'X-CSRFToken': csrftoken } : {},
            data: { rut: rut }
        });
    }

    function mostrarPopupCrear(data, rut) {
        const msg = (data && data.message) || 'Sin mensaje';
        const confirmText = (data && data.confirm_text) || 'Crear ficha';
        const createUrl = data && data.create_url;

        if (window.Swal && Swal.fire) {
            Swal.fire({
                title: 'Ficha no encontrada',
                html: `<p>${msg}</p><p style="margin-top:8px;">${confirmText}</p>`,
                icon: 'info',
                showCancelButton: true,
                confirmButtonText: 'Crear ficha',
                cancelButtonText: 'Cancelar'
            }).then(function (result) {
                if (result.isConfirmed) {
                    Swal.showLoading();
                    crearFichaAutomaticamente(rut, createUrl)
                        .done(function (resp) {
                            if (resp && resp.redirect_url) {
                                window.location.href = resp.redirect_url;
                            } else {
                                Swal.fire('Creado', 'Ficha creada, pero no se recibió URL de redirección.', 'success');
                            }
                        })
                        .fail(function (xhr) {
                            const detail = (xhr.responseJSON && (xhr.responseJSON.detail || xhr.responseJSON.message)) || 'Error al crear la ficha.';
                            Swal.fire('Error', detail, 'error');
                        });
                }
            });
        } else {
            // Fallback sin SweetAlert2
            if (confirm(`${msg}\n\n${confirmText}`)) {
                crearFichaAutomaticamente(rut, createUrl)
                    .done(function (resp) {
                        if (resp && resp.redirect_url) {
                            window.location.href = resp.redirect_url;
                        }
                    });
            }
        }
    }

    // Evitar que ENTER envíe el formulario
    $rutField.on('keydown', function (e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            return false;
        }
    });

    // Evento al salir del campo
    $rutField.on('blur', function () {
        const rut = normalizeRut($rutField.val());
        if (!rut || rut === lastRut) return;

        lastRut = rut;

        // Limpiar formulario para evitar datos residuales (conservar el RUT digitado)
        if (typeof window.resetPacienteForm === 'function') {
            window.resetPacienteForm();
        } else {
            // Fallback mínimo
            var $pacIdHidden = $('#paciente_id_hidden');
            if ($pacIdHidden.length) {
                $pacIdHidden.val('').trigger('change');
            }
            $('#ficha_id_hidden').val('');
            $('#form_action_hidden').val('add');
        }

        console.log('[rut_scan] Consultando RUT:', rut);

        $.ajax({
            url: '/api/ingreso-paciente-ficha/',
            type: 'GET',
            dataType: 'json',
            data: { search: rut, tipo: 'rut' },
            success: function (data) {
                console.log('[rut_scan] Respuesta API:', data);
                // Si backend devuelve estructura especial
                if (data && data.status) {
                    if (data.status === 'missing_ficha') {
                        mostrarPopupCrear(data, rut);
                        return;
                    }
                    if (data.status === 'not_found') {
                        if (typeof window.resetPacienteForm === 'function') {
                            window.resetPacienteForm();
                        }
                        const msg = `El paciente con el RUT ${rut} no existe en el sistema. Presione Continuar para agregar todos sus datos personales en su establecimiento.`;
                        if (window.Swal && Swal.fire) {
                            Swal.fire({
                                title: 'Paciente no existe',
                                text: msg,
                                icon: 'info',
                                confirmButtonText: 'Continuar'
                            });
                        } else {
                            alert(msg);
                        }
                        return;
                    }
                }

                const items = Array.isArray(data) ? data : (data.results || []);
                if (items.length > 0) {
                    const first = items[0];
                    if (first && typeof first.id !== 'undefined') {
                        console.log('[rut_scan] Cargando ficha:', first.id);
                        if (typeof window.cargarDatosFicha === 'function') {
                            window.cargarDatosFicha(first.id);
                        }
                    }
                } else {
                    console.log('[rut_scan] No se encontró ficha para RUT:', rut);
                }
            },
            error: function (xhr, status, error) {
                console.error('[rut_scan] Error en AJAX:', status, error);
                if (xhr && xhr.responseJSON && xhr.responseJSON.status === 'not_found') {
                    if (typeof window.resetPacienteForm === 'function') {
                        window.resetPacienteForm();
                    }
                    const msg = `El paciente con el RUT ${rut} no existe en el sistema. Presione Continuar para agregar todos sus datos personales en su establecimiento.`;
                    if (window.Swal && Swal.fire) {
                        Swal.fire({
                            title: 'Paciente no existe',
                            text: msg,
                            icon: 'info',
                            confirmButtonText: 'Continuar'
                        });
                    } else {
                        alert(msg);
                    }
                }
            }
        });
    });
});
