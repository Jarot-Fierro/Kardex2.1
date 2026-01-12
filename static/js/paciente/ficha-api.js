// static/js/paciente/ficha-api.js

$(document).ready(function () {

    $('.select2').select2({width: '100%'});

    let consultando = false;
    let ultimoRutConsultado = null;

    function limpiarFormularioPaciente() {

        const rutActual = $('#id_rut').val();

        $('#paciente-form')
            .find('input[type="text"], input[type="date"], textarea')
            .val('');

        $('#paciente-form')
            .find('input[type="checkbox"]')
            .prop('checked', false);

        $('#id_paciente_id').val('');

        $('#paciente-form select')
            .val(null)
            .trigger('change');

        $('#id_rut').val(rutActual);

        setText('id_usuario_anterior', '—');
        setText('id_fecha_creacion', '—');
        setText('id_servicio_clinico', '—');
        setText('id_profesional_cargo', '—');
        setText('id_fecha_envio', '—');

        $('#tabla-fichas tbody').empty();
    }

    function buscarPacientePorRut() {

        if (consultando) return;

        let rut = $('#id_rut').val().trim();
        if (!rut) return;

        rut = formatearRutString(rut);
        $('#id_rut').val(rut);

        if (rut === ultimoRutConsultado) return;

        consultando = true;
        ultimoRutConsultado = rut;

        $.ajax({
            url: `/personas/ficha-paciente/${rut}`,
            type: 'GET',
            dataType: 'json',

            success: function (response) {

                limpiarFormularioPaciente();

                cargarPaciente(response);
                cargarFicha(response);
                cargaTabla(response);
                cargaUbicacionFicha(response);

                if (window.actualizarReglasPaciente) window.actualizarReglasPaciente();
                if (window.actualizarEstadoFallecimiento) window.actualizarEstadoFallecimiento();

                $('#ver_movimientos').removeClass('d-none');
            },

            error: function () {

                limpiarFormularioPaciente();
                $('#ver_movimientos').addClass('d-none');
                ultimoRutConsultado = null;

                alert('Paciente no encontrado');
            },

            complete: function () {
                consultando = false;
            }
        });
    }

    $('#id_rut').on('keyup blur', e => {
        if (e.type === 'keyup' && e.key !== 'Enter') return;
        e.preventDefault();
        buscarPacientePorRut();
    });

    $('#btn-consultar-denuevo').on('click', function () {
        ultimoRutConsultado = null;
        buscarPacientePorRut();
    });

    /* MODO VISTA */
    const modo = document.getElementById('modo-vista')?.value;

    if (modo === 'consulta') {
        ocultarErroresFormulario();
        limpiarFormularioPaciente();
    }

});
