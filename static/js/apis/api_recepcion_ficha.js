(function () {
  function debounce(fn, wait) {
    let t;
    return function (...args) {
      clearTimeout(t);
      t = setTimeout(() => fn.apply(this, args), wait);
    };
  }

  function getVal($el) { return ($el && $el.length) ? $el.val() : null; }
  function setVal(selector, value) { const $el = $(selector); if ($el.length) $el.val(value); }
  function clearFields() {
    setVal('#nombre_mov', '');
    setVal('#id_ficha', '');
    // No limpiar servicio si el usuario ya escogió uno manualmente
  }

  function fillFromDetail(data) {
    const f = data.ficha || {};
    const p = f.paciente || {};

    const nombreCompleto = `${p.nombre || ''} ${p.apellido_paterno || ''} ${p.apellido_materno || ''}`.trim();
    setVal('#nombre_mov', nombreCompleto);

    if (p.rut) setVal('#id_rut', p.rut);

    if (f.numero_ficha_sistema) setVal('#id_ficha', f.numero_ficha_sistema);

    // Servicio Clínico de envío (origen) puede ser texto (input) o select
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
        const valorEnvio = data.servicio_clinico_envio_nombre || data.servicio_clinico_envio || '';
        $svcEnvio.val(valorEnvio);
      }
    }

    // Servicio clínico de recepción puede ser texto (input) o un select
    const $svc = $('#servicio_clinico_ficha');
    if ($svc.length) {
      const tag = ($svc.prop('tagName') || '').toLowerCase();
      const type = ($svc.attr('type') || '').toLowerCase();
      const isSelect = tag === 'select';
      const isTextInput = tag === 'input' && (type === 'text' || type === 'search' || type === '');

      if (isSelect) {
        // Si es select, asumimos que la API entrega el ID del servicio
        if (typeof data.servicio_clinico_recepcion !== 'undefined' && data.servicio_clinico_recepcion !== null) {
          $svc.val(data.servicio_clinico_recepcion).trigger('change');
        }
      } else if (isTextInput) {
        // Si es input de texto, intentamos rellenar el nombre del servicio
        const nombreServicio =
          data.servicio_clinico_recepcion_nombre ||
          data.servicio_clinico_recepcion_text ||
          data.servicio_clinico_recepcion_label ||
          data.servicio_clinico_recepcion_name ||
          (typeof data.servicio_clinico_recepcion === 'string' ? data.servicio_clinico_recepcion : '') ||
          (data.servicio_clinico_recepcion && data.servicio_clinico_recepcion.nombre ? data.servicio_clinico_recepcion.nombre : '');
        $svc.val(nombreServicio || '');
      } else {
        // Para cualquier otro caso, intentar asignar algo razonable
        const valor =
          data.servicio_clinico_recepcion_nombre ||
          data.servicio_clinico_recepcion || '';
        $svc.val(valor);
      }
    }

    if (typeof data.observacion_recepcion !== 'undefined') {
      setVal('#observacion_recepcion_ficha', data.observacion_recepcion || '');
    }
  }

  function fetchDetailByMovementId(movId) {
    return new Promise(function(resolve) {
      $.ajax({
        url: `/api/recepcion-ficha/${movId}/`,
        method: 'GET',
        success: function (data) { fillFromDetail(data); resolve(true); },
        error: function () { console.warn('No se pudo obtener el detalle de la recepción'); resolve(false); }
      });
    });
  }

  let lastRutSearched = null;
  let inflightPromise = null;

  function searchByRut(rut) {
    if (!rut) { clearFields(); lastRutSearched = null; return Promise.resolve(false); }
    lastRutSearched = rut;
    inflightPromise = new Promise(function(resolve) {
      $.ajax({
        url: '/api/recepcion-ficha/',
        dataType: 'json',
        data: { search: rut },
        success: function (data) {
          const results = (data && data.results) || [];
          if (!results.length) { clearFields(); resolve(false); return; }
          // Buscar coincidencia exacta por texto (rut); si no, tomar el primero
          let item = results.find(r => (r.text || '').toUpperCase() === rut.toUpperCase());
          if (!item) item = results[0];
          if (item && item.id) {
            fetchDetailByMovementId(item.id).then(resolve);
          } else { clearFields(); resolve(false); }
        },
        error: function () { console.warn('Error buscando por RUT'); resolve(false); }
      });
    });
    return inflightPromise;
  }

  function ensureApiBeforeSubmit() {
    const $rut = $('#id_rut');
    const currentRut = getVal($rut);
    const nombre = getVal($('#nombre_mov')) || '';
    const ficha = getVal($('#id_ficha')) || '';

    // Si ya está all cargado, continuar
    if (currentRut && nombre.trim() && ficha.trim()) {
      return Promise.resolve(true);
    }

    // Si no coincide con la última búsqueda o información vacía, hacer búsqueda
    if (currentRut && currentRut !== lastRutSearched) {
      return searchByRut(currentRut);
    }

    // Si hay una búsqueda en curso, esperar; si no, intentar buscar de nuevo
    if (inflightPromise) return inflightPromise;
    if (currentRut) return searchByRut(currentRut);

    // Si no hay RUT, no podemos consumir la API
    return Promise.resolve(false);
  }

  $(function () {
    const $rut = $('#id_rut');
    if (!$rut.length) return;

    // Ejecuta al perder el foco
    $rut.on('blur', function () { searchByRut(getVal($rut)); });

    // Y también con debounce mientras escribe
    $rut.on('input', debounce(function () { searchByRut(getVal($rut)); }, 500));

    // Antes de enviar el formulario, aseguremos que la API se haya consumido y los campos estén completos
    const $form = $('#form-recepcion');
    $form.on('submit', function (e) {
      // Si ya tenemos datos, permitir envío
      const nombre = getVal($('#nombre_mov')) || '';
      const ficha = getVal($('#id_ficha')) || '';
      const rutVal = getVal($rut) || '';
      if (rutVal && nombre.trim() && ficha.trim()) {
        return true;
      }

      e.preventDefault();
      $('#btn-guardar').prop('disabled', true).text('Guardando...');

      ensureApiBeforeSubmit().then(function (ok) {
        if (ok) {
          // Verificar nuevamente datos necesarios
          const nombre2 = getVal($('#nombre_mov')) || '';
          const ficha2 = getVal($('#id_ficha')) || '';
          if (nombre2.trim() && ficha2.trim()) {
            // Enviar realmente el formulario
            $form.off('submit');
            $form.trigger('submit');
            return;
          }
        }
        // Si falla, habilitar botón y avisar
        $('#btn-guardar').prop('disabled', false).text('Guardar');
        // Usar SweetAlert2 si está disponible, si no, alert()
        if (window.Swal) {
          Swal.fire({ icon: 'warning', title: 'Datos incompletos', text: 'Ingrese un RUT válido para completar automáticamente los datos antes de guardar.' });
        } else {
          alert('Datos incompletos: Ingrese un RUT válido para completar automáticamente los datos antes de guardar.');
        }
      });
    });
  });
})();