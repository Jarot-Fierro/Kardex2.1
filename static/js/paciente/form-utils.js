// static/js/paciente/form-utils.js

function setValue(id, value) {
    const $el = $('#' + id);
    if (!$el.length) return;

    if ($el.is(':checkbox')) {
        $el.prop('checked', !!value);
    } else {
        $el.val(value ?? '');
    }
}

function setText(id, value) {
    const $el = $('#' + id);
    if (!$el.length) return;
    $el.text(value ?? '—');
}

function setSelect2ById(id, value) {
    const $el = $('#' + id);
    if (!$el.length) return;

    if (value === null || value === undefined || value === '') {
        $el.val(null).trigger('change');
        return;
    }

    $el.val(String(value)).trigger('change.select2');
}

function formatearRutString(rut) {
    rut = rut.replace(/\./g, '').replace(/-/g, '').toUpperCase();
    if (rut.length <= 1) return rut;

    const cuerpo = rut.slice(0, -1);
    const dv = rut.slice(-1);

    return cuerpo.replace(/\B(?=(\d{3})+(?!\d))/g, '.') + '-' + dv;
}

function formatearFechaHora(fechaIso) {
    if (!fechaIso) return '—';

    const fecha = new Date(fechaIso);
    if (isNaN(fecha.getTime())) return '—';

    const dia = String(fecha.getDate()).padStart(2, '0');
    const mes = String(fecha.getMonth() + 1).padStart(2, '0');
    const anio = fecha.getFullYear();
    const horas = String(fecha.getHours()).padStart(2, '0');
    const minutos = String(fecha.getMinutes()).padStart(2, '0');

    return `${dia}-${mes}-${anio} ${horas}:${minutos}`;
}

function ocultarErroresFormulario() {
    $('#paciente-form .invalid-feedback').addClass('d-none');
    $('#paciente-form .is-invalid').removeClass('is-invalid');
}
