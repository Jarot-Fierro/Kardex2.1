/* global $ */
function apiLookup(params, cb){
  $.get(window.location.origin + (window.KARDEX_LOOKUP_URL || '/kardex/api/movimiento-ficha-lookup/'), params)
    .done(function(resp){ cb(null, resp); })
    .fail(function(xhr){ cb(xhr); });
}

function initAutocompletarFicha(rutSelector, fichaSelector, nombreSelector){
  const $rut = $(rutSelector);
  const $ficha = $(fichaSelector);
  const $nom = $(nombreSelector);
  $rut.on('change blur', function(){
    const rut = ($rut.val() || '').trim();
    if(!rut){ return; }
    apiLookup({ rut: rut }, function(err, resp){
      if(err){ return; }
      if(resp && resp.ok && resp.results && resp.results.length){
        const r = resp.results[0];
        if(r.numero_ficha && !$ficha.val()) $ficha.val(r.numero_ficha);
        if(r.nombre_completo) $nom.val(r.nombre_completo);
      }
    });
  });
}

function initAutocompletarFichaByFicha(fichaSelector, rutSelector, nombreSelector){
  const $ficha = $(fichaSelector);
  const $rut = $(rutSelector);
  const $nom = $(nombreSelector);
  $ficha.on('change blur', function(){
    const nf = ($ficha.val() || '').trim();
    if(!nf){ return; }
    apiLookup({ ficha: nf }, function(err, resp){
      if(err){ return; }
      if(resp && resp.ok && resp.results && resp.results.length){
        const r = resp.results[0];
        if(r.rut && !$rut.val()) $rut.val(r.rut);
        if(r.nombre_completo) $nom.val(r.nombre_completo);
      }
    });
  });
}
