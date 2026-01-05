$(function () {
  // Inicializa select2 en el campo RUT del formulario de traspaso
  const $rut = $('#id_rut');
  if (!$rut.length) return;

  // Helper: set value safely if element exists
  function setVal(selector, value) {
    const $el = $(selector);
    if ($el.length) $el.val(value == null ? '' : value);
  }

  function nombreCompleto(p) {
    if (!p) return '';
    return `${p.nombre || ''} ${p.apellido_paterno || ''} ${p.apellido_materno || ''}`.trim();
  }

  // Flag simple para evitar múltiples llamadas concurrentes en blur/paste/enter
  let querying = false;

  // Si el campo es SELECT, usamos select2; si es INPUT, usamos blur/paste/enter
  const isSelect = $rut.is('select');
  if (isSelect) {
    $rut.select2({
      placeholder: 'Buscar por RUT o N° ficha',
      width: '100%',
      ajax: {
        url: '/api/traspaso-ficha/',
        dataType: 'json',
        delay: 250,
        data: function (params) {
          return { search: params.term };
        },
        processResults: function (data) {
          const items = Array.isArray(data) ? data : (data.results || []);
          const results = items.map(item => {
            const f = item.ficha || {};
            const p = f.paciente || {};
            const rut = p.rut || '';
            const nombre = nombreCompleto(p);
            const nf = f.numero_ficha_sistema || '';
            return {
              id: item.id, // ID del movimiento
              text: `${rut}`,
              extra: { nombre, nf }
            };
          });
          return { results };
        }
      },
      minimumInputLength: 1,
      theme: 'bootstrap4'
    });

    $rut.on('select2:select', function (e) {
      const movId = e.params.data.id;
      if (movId) cargarMovimiento(movId);
    });
  } else {
    // INPUT de texto: consumir API al hacer clic fuera, pegar o presionar Enter
    function normalizar(valor) {
      return String(valor || '').trim().toUpperCase();
    }

    function consultarPorTermino(term) {
      const q = normalizar(term);
      if (!q || querying) return;
      querying = true;
      $.ajax({
        url: '/api/traspaso-ficha/',
        method: 'GET',
        dataType: 'json',
        data: { search: q },
        success: function (data) {
          const items = Array.isArray(data) ? data : (data.results || []);
          if (!items.length) {
            console.log('[api_traspaso_ficha] Sin resultados para', q);
            return;
          }
          // Intentar coincidencia exacta por RUT si viene anidado
          const exact = items.find(it => {
            try { return normalizar(it.ficha.paciente.rut) === q; } catch (e) { return false; }
          });
          const chosen = exact || items[0];
          if (chosen && chosen.id) {
            cargarMovimiento(chosen.id);
          }
        },
        error: function (err) {
          console.error('[api_traspaso_ficha] Error consultando API:', err);
        },
        complete: function () {
          // liberar después de un tick para evitar dobles blur/paste encadenados
          setTimeout(function(){ querying = false; }, 150);
        }
      });
    }

    $rut.on('blur', function () {
      consultarPorTermino($rut.val());
    });
    $rut.on('paste', function () {
      setTimeout(function(){ consultarPorTermino($rut.val()); }, 60);
    });
    $rut.on('keydown', function (e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        consultarPorTermino($rut.val());
      }
    });
  }

  function cargarMovimiento(movId) {
    $.ajax({
      url: `/api/traspaso-ficha/${movId}/`,
      method: 'GET',
      success: function (data) {
        const f = data.ficha || {};
        const p = f.paciente || {};

        // Relleno de campos comunes
        const rut = p.rut || '';
        const nombre = nombreCompleto(p);
        setVal('#nombre_mov', nombre);

        if (rut) {
          // Si es SELECT, crear opción; si es INPUT, sólo setear valor
          if ($rut.is('select')) {
            const optRut = new Option(rut, rut, true, true);
            $rut.empty().append(optRut).trigger('change');
          } else {
            $rut.val(rut);
          }
        }

        // Ficha: el input usa ID visual: id_ficha, pero el valor esperado por clean_ficha es numero
        const numeroFicha = f.numero_ficha_sistema || '';
        if (numeroFicha) {
          // Si fuese un select, generar Option; si es input text, setear valor
          const $ficha = $('#id_ficha');
          if ($ficha.is('select')) {
            const optFicha = new Option(numeroFicha, numeroFicha, true, true);
            $ficha.empty().append(optFicha).trigger('change');
          } else {
            $ficha.val(numeroFicha).trigger('input');
          }
        } else {
          $('#id_ficha').val('').trigger('change');
        }

        // Servicios clínicos mostrados como texto
        const svcEnvio = (data.servicio_clinico_envio && data.servicio_clinico_envio.nombre) || '';
        const svcRec = (data.servicio_clinico_recepcion && data.servicio_clinico_recepcion.nombre) || '';
        const svcTrasp = (data.servicio_clinico_traspaso && data.servicio_clinico_traspaso.nombre) || '';
        setVal('#servicio_clinico_envio_ficha', svcEnvio);
        setVal('#servicio_clinico_recepcion_ficha', svcRec);
        setVal('#servicio_clinico_ficha', svcTrasp);

        // Observaciones
        setVal('#observacion_envio_ficha', data.observacion_envio || '');
        setVal('#observacion_recepcion_ficha', data.observacion_recepcion || '');
        setVal('#observacion_traspaso_ficha', data.observacion_traspaso || '');

        // Estados
        setVal('#id_estado_envio', data.estado_envio || '');
        setVal('#id_estado_recepcion', data.estado_recepcion || '');
        setVal('#id_estado_traspaso', data.estado_traspaso || '');

        // Fechas
        function toLocalInput(dtStr) {
          if (!dtStr) return '';
          try {
            // 1) Si viene en ISO con offset o Z, extraemos la parte local sin aplicar desfase
            // Ej: 2025-10-27T12:43:00-03:00 -> 2025-10-27T12:43
            const m = String(dtStr).match(/^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2})(?::\d{2}(?:\.\d{1,6})?)?(?:Z|[+-]\d{2}:?\d{2})?$/);
            if (m) {
              return `${m[1]}T${m[2]}`; // YYYY-MM-DDTHH:MM
            }
            // 2) Intentar parsear cualquier otro formato con Date y formatear a datetime-local
            const d = new Date(dtStr);
            if (!isNaN(d.getTime())) {
              const pad = n => String(n).padStart(2, '0');
              return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
            }
            return '';
          } catch (e) { return ''; }
        }
        const vEnv = toLocalInput(data.fecha_envio);
        const vRec = toLocalInput(data.fecha_recepcion);
        const vTra = toLocalInput(data.fecha_traspaso);
        // Intentar con IDs usados en otras pantallas y los IDs por defecto de Django
        setVal('#fecha_envio_ficha', vEnv);  // usado en salida
        setVal('#id_fecha_envio', vEnv);     // id por defecto en este form
        setVal('#fecha_recepcion_ficha', vRec); // usado en recepción
        setVal('#id_fecha_recepcion', vRec);
        setVal('#fecha_traspaso_ficha', vTra);   // id personalizado en este form
        setVal('#id_fecha_traspaso', vTra);

        // Profesional traspaso si viene
        if (data.profesional_traspaso && data.profesional_traspaso.id) {
          const $prof = $('#profesional_movimiento');
          if ($prof.is('select')) {
            // Para compatibilidad: algunos modelos usan 'nombres' en el serializer
            const label = [
              data.profesional_traspaso.nombres,
              data.profesional_traspaso.nombre,
              data.profesional_traspaso.apellido_paterno,
              data.profesional_traspaso.apellido_materno
            ].filter(Boolean).join(' ').trim();
            const opt = new Option(label || 'Profesional', data.profesional_traspaso.id, true, true);
            $prof.append(opt).trigger('change');
          }
        }
      },
      error: function (err) {
        console.error('Error cargando movimiento para traspaso:', err);
      }
    });
  }
});
