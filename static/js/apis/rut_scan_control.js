(function(){
  function debounce(fn, wait){
    let t; return function(){
      const ctx=this, args=arguments; clearTimeout(t);
      t=setTimeout(function(){ fn.apply(ctx,args); }, wait);
    };
  }

  function normalizeRut(val){
    if(!val) return '';
    return String(val).trim();
  }

  document.addEventListener('DOMContentLoaded', function(){
    var $rut = document.getElementById('id_rut');
    if(!$rut) return;

    // Prevent default scanner Enter from submitting the form immediately
    var form = $rut.form || document.querySelector('form');
    var lastInputTs = 0;

    $rut.addEventListener('keydown', function(e){
      if(e.key === 'Enter'){
        e.preventDefault();
        e.stopPropagation();
        return false;
      }
    });

    // If for any reason submit fires right after paste/input, block it briefly
    if(form){
      form.addEventListener('submit', function(e){
        var now = Date.now();
        if(now - lastInputTs < 600){
          // Block auto-submit triggered by scanner
          e.preventDefault();
          e.stopPropagation();
          return false;
        }
      }, true);
    }

    var runQuery = debounce(function(){
      var rut = normalizeRut($rut.value || '');
      if(!rut) return;

      // Marca momento de última edición para bloquear submits inmediatos
      lastInputTs = Date.now();

      // Consumir API para determinar existencia por RUT
      var url = '/api/ingreso-paciente-ficha/';
      var params = new URLSearchParams({ search: rut, tipo: 'rut' });
      fetch(url + '?' + params.toString(), {
        method: 'GET',
        headers: { 'Accept': 'application/json' }
      })
      .then(function(res){ return res.json().catch(function(){ return {}; }); })
      .then(function(data){
        var items = Array.isArray(data) ? data : (data.results || []);
        var existe = Array.isArray(items) && items.length > 0;
        // Log y emitir evento para orquestar pasos siguientes (sin enviar formulario)
        console.log('[rut_scan_control] Consulta RUT', rut, 'existe=', existe, items);
        window.dispatchEvent(new CustomEvent('pacienteRutConsultado', {
          detail: { rut: rut, existe: existe, data: items }
        }));
      })
      .catch(function(err){
        console.warn('[rut_scan_control] Error consultando API de RUT:', err);
        window.dispatchEvent(new CustomEvent('pacienteRutConsultado', {
          detail: { rut: rut, existe: false, data: [], error: true }
        }));
      });
    }, 200);

    // Detectar cambios por input y pegado
    $rut.addEventListener('input', runQuery);
    $rut.addEventListener('paste', function(){
      // Se ejecutará tras pegar
      setTimeout(runQuery, 0);
    });
  });
})();
