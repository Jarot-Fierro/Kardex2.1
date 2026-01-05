// Inicialización de Select2 para formulario de Movimiento de Ficha
// - Para campos con endpoints disponibles, se usa AJAX
// - Para el resto, se inicializa Select2 estándar (sin AJAX) para mejorar UX

(function () {
  $(function () {
    // Helper común
    function initBasicSelect2(selector, placeholder) {
      const $el = $(selector);
      if (!$el.length) return;
      $el.select2({
        theme: 'bootstrap4',
        width: '100%',
        placeholder: placeholder || 'Seleccione…',
        allowClear: true
      });
    }

    // 1) Ficha: usar endpoint existente /api/ingreso-paciente-ficha/
    const $ficha = $('#id_ficha');
    if ($ficha.length) {
      try {
        $ficha.select2({
          theme: 'bootstrap4',
          width: '100%',
          placeholder: 'Buscar por número de ficha',
          ajax: {
            url: '/api/ingreso-paciente-ficha/',
            dataType: 'json',
            delay: 250,
            data: function (params) {
              return { search: params.term, tipo: 'ficha' };
            },
            processResults: function (data) {
              const results = (data.results || []).map(function (item) {
                const num = String(item.numero_ficha_sistema || item.numero_ficha || item.id);
                return { id: item.id, text: `Ficha: ${num}` };
              });
              return { results: results };
            }
          },
          minimumInputLength: 1
        });
      } catch (e) {
        // Fallback
        initBasicSelect2('#id_ficha', 'Seleccione una ficha');
      }
    }

        // 2) Servicio Clínico (envío/recepción/traspaso): AJAX
    function ajaxServicio(selector, placeholder) {
      const $el = $(selector);
      if (!$el.length) return;
      $el.select2({
        theme: 'bootstrap4',
        width: '100%',
        placeholder: placeholder || 'Seleccione servicio clínico',
        allowClear: true,
        ajax: {
          url: '/api/servicios-clinicos/',
          dataType: 'json',
          delay: 250,
          data: function (params) { return { search: params.term }; },
          processResults: function (data) {
            const results = (data.results || data || []).map(function (item) {
              return { id: item.id, text: item.nombre };
            });
            return { results: results };
          }
        },
        minimumInputLength: 1
      });
    }
    ajaxServicio('#id_servicio_clinico_envio', 'Seleccione servicio de envío');
    ajaxServicio('#id_servicio_clinico_recepcion', 'Seleccione servicio de recepción');
    ajaxServicio('#id_servicio_clinico_traspaso', 'Seleccione servicio de traspaso');

    // 3) Profesionales (envío/recepción/traspaso): AJAX
    function ajaxProfesional(selector, placeholder) {
      const $el = $(selector);
      if (!$el.length) return;
      $el.select2({
        theme: 'bootstrap4',
        width: '100%',
        placeholder: placeholder || 'Seleccione profesional',
        allowClear: true,
        ajax: {
          url: '/api/profesionales/',
          dataType: 'json',
          delay: 250,
          data: function (params) { return { search: params.term }; },
          processResults: function (data) {
            const results = (data.results || data || []).map(function (item) {
              const nombre = [item.nombres, item.apellido_paterno, item.apellido_materno].filter(Boolean).join(' ');
              return { id: item.id, text: nombre || ('ID ' + item.id) };
            });
            return { results: results };
          }
        },
        minimumInputLength: 1
      });
    }
    ajaxProfesional('#id_profesional_envio', 'Seleccione profesional que envía');
    ajaxProfesional('#id_profesional_recepcion', 'Seleccione profesional que recibe');
    ajaxProfesional('#id_profesional_traspaso', 'Seleccione profesional que traslada');

    // 4) Usuarios del sistema relacionados: Select2 básico
    initBasicSelect2('#id_usuario_envio', 'Seleccione usuario envío');
    initBasicSelect2('#id_usuario_recepcion', 'Seleccione usuario recepción');
    initBasicSelect2('#id_usuario_traspaso', 'Seleccione usuario traspaso');

    // 5) Campos adicionales posibles como establecimiento / usuarios anteriores
    initBasicSelect2('#id_establecimiento', 'Seleccione establecimiento');
    initBasicSelect2('#id_usuario_envio_anterior', 'Seleccione usuario envío anterior');
    initBasicSelect2('#id_usuario_recepcion_anterior', 'Seleccione usuario recepción anterior');

    // 6) Mejoras para textareas largos
    $('textarea').attr('rows', function (i, val) {
      return val || 2;
    });
  });
})();
