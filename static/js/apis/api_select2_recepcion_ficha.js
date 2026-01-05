$(function () {
  // Inicializa select2 en el campo RUT del formulario de recepción
  const $rut = $('#id_rut');
  if (!$rut.length) return;

  $rut.select2({
    placeholder: 'Buscar por RUT',
    width: '100%',
    ajax: {
      url: '/api/recepcion-ficha/',
      dataType: 'json',
      delay: 250,
      data: function (params) {
        return { search: params.term };
      },
      processResults: function (data) {
        const results = (data.results || []).map(item => {
          const paciente = (item.ficha && item.ficha.paciente) || {};
          const rut = paciente.rut || '';
          const nombre = `${paciente.nombre || ''} ${paciente.apellido_paterno || ''} ${paciente.apellido_materno || ''}`.trim();
          return {
            id: item.id,  // ID del movimiento (se usa para cargar detalles)
            text: `${rut}`
          };
        });
        return { results };
      }
    },
    minimumInputLength: 1
  });

  // Cuando se selecciona un resultado, cargar y rellenar el formulario
  $rut.on('select2:select', function (e) {
    const movId = e.params.data.id;
    if (movId) llenarPorMovimiento(movId);
  });

  function llenarPorMovimiento(movId) {
    $.ajax({
      url: `/api/recepcion-ficha/${movId}/`,
      method: 'GET',
      success: function (data) {
        console.log('Datos recibidos en llenarPorMovimiento:', data);

        const f = data.ficha || {};
        const p = (f.paciente) || {};

        const nombreCompleto = `${p.nombre || ''} ${p.apellido_paterno || ''} ${p.apellido_materno || ''}`.trim();
        $('#nombre_mov').val(nombreCompleto);

        if (p.rut) {
          const optRut = new Option(p.rut, p.rut, true, true);
          $('#id_rut').empty().append(optRut).trigger('change');
          console.log('Opción RUT agregada y seleccionada:', p.rut);
        }

        if (f.numero_ficha_sistema && f.id) {
          const optFicha = new Option(f.numero_ficha_sistema, f.id, true, true);
          $('#id_ficha').empty().append(optFicha).trigger('change');
          console.log('Opción Ficha agregada y seleccionada:', f.numero_ficha_sistema);
        } else {
          // Si no viene ficha en la respuesta, limpiar el select para evitar valores obsoletos
          $('#id_ficha').empty().trigger('change');
        }

        // Servicio clínico de envío (origen) puede ser un select (id) o un input de texto (nombre)
        (function(){
          const $svcEnvio = $('#servicio_clinico_envio_ficha');
          if ($svcEnvio.length) {
            const tag = ($svcEnvio.prop('tagName') || '').toLowerCase();
            const type = ($svcEnvio.attr('type') || '').toLowerCase();
            const isSelect = tag === 'select';
            const isTextInput = tag === 'input' && (type === 'text' || type === 'search' || type === '');
            if (isSelect) {
              if (typeof data.servicio_clinico_envio !== 'undefined' && data.servicio_clinico_envio !== null) {
                $svcEnvio.val(data.servicio_clinico_envio).trigger('change');
              }
            } else if (isTextInput) {
              const nombreServicioEnvio =
                data.servicio_clinico_envio_nombre ||
                data.servicio_clinico_envio_text ||
                data.servicio_clinico_envio_label ||
                data.servicio_clinico_envio_name ||
                (typeof data.servicio_clinico_envio === 'string' ? data.servicio_clinico_envio : '') ||
                (data.servicio_clinico_envio && data.servicio_clinico_envio.nombre ? data.servicio_clinico_envio.nombre : '');
              $svcEnvio.val(nombreServicioEnvio || '');
            } else {
              const valorEnvio =
                data.servicio_clinico_envio_nombre ||
                data.servicio_clinico_envio || '';
              $svcEnvio.val(valorEnvio);
            }
          }
        })();

        // Servicio clínico de recepción puede ser un select (id) o un input de texto (nombre)
        (function(){
          const $svc = $('#servicio_clinico_ficha');
          if ($svc.length) {
            const tag = ($svc.prop('tagName') || '').toLowerCase();
            const type = ($svc.attr('type') || '').toLowerCase();
            const isSelect = tag === 'select';
            const isTextInput = tag === 'input' && (type === 'text' || type === 'search' || type === '');
            if (isSelect) {
              if (typeof data.servicio_clinico_recepcion !== 'undefined' && data.servicio_clinico_recepcion !== null) {
                $svc.val(data.servicio_clinico_recepcion).trigger('change');
              }
            } else if (isTextInput) {
              const nombreServicio =
                data.servicio_clinico_recepcion_nombre ||
                data.servicio_clinico_recepcion_text ||
                data.servicio_clinico_recepcion_label ||
                data.servicio_clinico_recepcion_name ||
                (typeof data.servicio_clinico_recepcion === 'string' ? data.servicio_clinico_recepcion : '') ||
                (data.servicio_clinico_recepcion && data.servicio_clinico_recepcion.nombre ? data.servicio_clinico_recepcion.nombre : '');
              $svc.val(nombreServicio || '');
            } else {
              const valor =
                data.servicio_clinico_recepcion_nombre ||
                data.servicio_clinico_recepcion || '';
              $svc.val(valor);
            }
          }
        })();
        // No preseleccionamos profesional_recepcion; lo debe escoger el usuario
        if (typeof data.observacion_recepcion !== 'undefined') $('#observacion_recepcion_ficha').val(data.observacion_recepcion || '');
      },
      error: function (err) {
        console.error('Error en AJAX:', err);
      }
    });
  }
});

