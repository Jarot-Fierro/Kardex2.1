$(document).ready(function () {
    const $rutField = $('#id_rut');
    const $form = $('#form-salida');
    if ($rutField.length === 0) return;

    let lastRut = null;
    let autoSubmitting = false;

    function normalizeRut(rut) {
        return String(rut || '').trim().toUpperCase();
    }

    function procesarRut() {
        const rut = normalizeRut($rutField.val());
        if (!rut || rut === lastRut || autoSubmitting) return;
        lastRut = rut;

        console.log('[rut_scan_salida] Consultando RUT:', rut);

        $.ajax({
            url: '/api/ingreso-paciente-ficha/',
            type: 'GET',
            dataType: 'json',
            data: { search: rut, tipo: 'rut' },
            success: function (data) {
                console.log('[rut_scan_salida] Respuesta API:', data);
                const items = Array.isArray(data) ? data : (data.results || []);
                if (items.length > 0) {
                    const first = items[0];
                    if (first && typeof first.id !== 'undefined') {
                        console.log('[rut_scan_salida] Cargando ficha salida:', first.id);
                        if (typeof window.cargarDatosSalidaFicha === 'function') {
                            window.cargarDatosSalidaFicha(first.id);
                        } else if (typeof window.cargarDatosFicha === 'function') {
                            // Fallback si no existe la función específica
                            window.cargarDatosFicha(first.id);
                        }
                        // Enviar el formulario automáticamente luego de cargar datos
                        if ($form.length) {
                            autoSubmitting = true;
                            // Dar un pequeño margen para que la función de carga complete
                            setTimeout(function () {
                                try {
                                    console.log('[rut_scan_salida] Enviando formulario de salida automáticamente');
                                    $form.trigger('submit');
                                } finally {
                                    // Permite nuevos escaneos después de un breve lapso
                                    setTimeout(function(){ autoSubmitting = false; }, 1000);
                                }
                            }, 400);
                        }
                    }
                } else {
                    console.log('[rut_scan_salida] No se encontró ficha para RUT:', rut);
                }
            },
            error: function (xhr, status, error) {
                console.error('[rut_scan_salida] Error en AJAX:', status, error);
            }
        });
    }

    // Evento al salir del campo
    $rutField.on('blur', function () {
        procesarRut();
    });

    // Manejar pegado desde la pistola/portapapeles
    $rutField.on('paste', function () {
        setTimeout(procesarRut, 50);
    });
});