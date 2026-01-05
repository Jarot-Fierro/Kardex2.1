(function(){
    function debounce(fn, wait){
        let t; return function(){
            const ctx=this, args=arguments; clearTimeout(t);
            t=setTimeout(function(){ fn.apply(ctx,args); }, wait);
        };
    }

    function isBlank(v){ return v===undefined || v===null || String(v).trim()===''; }

    function buscarFichaPorNumero(numero){
        numero = String(numero || '').trim();
        if(!numero) return;
        const url = '/api/ingreso-paciente-ficha/';
        const params = new URLSearchParams({ search: numero, tipo: 'ficha' });
        return fetch(url + '?' + params.toString(), { headers: { 'Accept': 'application/json' }})
            .then(function(res){ return res.json().catch(function(){ return {}; }); })
            .then(function(data){
                const items = Array.isArray(data) ? data : (data.results || []);
                if(Array.isArray(items) && items.length > 0){
                    const first = items[0];
                    if(first && typeof first.id !== 'undefined'){
                        cargarDatosSalidaFicha(first.id);
                    }
                }
            })
            .catch(function(err){ console.warn('[handle_fichas_salida] Error buscando ficha:', err); });
    }

    window.cargarDatosSalidaFicha = function(fichaId){
        $.ajax({
            url: `/api/ingreso-paciente-ficha/${fichaId}/`,
            method: 'GET',
            success: function (data) {
                const paciente = data.paciente || {};

                // Rellenar nombre
                const nombreCompleto = `${paciente.nombre || ''} ${paciente.apellido_paterno || ''} ${paciente.apellido_materno || ''}`.trim();
                $('#nombre_mov').val(nombreCompleto);

                // Formatear número de ficha a 4 dígitos y setear en input texto
                const numeroFormateado = String(data.numero_ficha_sistema);
                $('#id_ficha').val(numeroFormateado);

                // Setear rut en su input texto (no select)
                if (!isBlank(paciente.rut)) {
                    $('#id_rut').val(paciente.rut).trigger('change');
                }

                // Notificar que la ficha fue cargada completamente
                try {
                    window.dispatchEvent(new CustomEvent('salidaFichaCargada', { detail: { fichaId: data.id, data: data } }));
                } catch (_) { /* noop */ }
            },
            error: function () {
                alert('Error al cargar los datos de la ficha.');
            }
        });
    };

    // Escuchar tipeo en el campo de ficha (input text) y buscar automáticamente
    $(document).ready(function(){
        var $ficha = $('#id_ficha');
        if($ficha.length){
            // Evitar submit accidental con Enter
            $ficha.on('keydown', function(e){ if(e.key==='Enter'){ e.preventDefault(); e.stopPropagation(); return false; } });
            var run = debounce(function(){
                var val = $ficha.val();
                // Permite ingresar con ceros a la izquierda: quitar ceros para buscar numérico
                var raw = String(val||'').trim();
                var normalized = raw.replace(/^0+/, '');
                if(normalized==='') normalized = raw; // si era all ceros, usar tal cual
                buscarFichaPorNumero(normalized);
            }, 300);
            $ficha.on('input', run);
            $ficha.on('paste', function(){ setTimeout(function(){ $ficha.trigger('input'); }, 0); });
        }
    });
})();
