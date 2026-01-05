$('#id_codigo').select2({
    placeholder: 'Buscar por código de paciente',
    width: '100%',
    ajax: {
        url: '/api/ingreso-paciente-ficha/',
        dataType: 'json',
        delay: 250,
        data: function (params) {
            return {
                search: params.term,
                tipo: 'codigo'
            };
        },
        processResults: function (data) {
            return {
                results: data.results.map(item => {
                    const paciente = item.paciente;
                    return {
                        id: item.id,
                        text: `${paciente.codigo}`
                    };
                })
            };
        }
    },
    minimumInputLength: 1
});

