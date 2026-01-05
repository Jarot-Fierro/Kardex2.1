$('#id_ficha').select2({
    placeholder: 'Buscar por número de ficha',
    width: '100%',
    ajax: {
        url: '/api/ingreso-paciente-ficha/',
        dataType: 'json',
        delay: 250,
        data: function (params) {
            return {
                search: params.term,
                tipo: 'ficha'
            };
        },
        processResults: function (data) {
            return {
                results: data.results.map(item => {
                    const num = String(item.numero_ficha_sistema).padStart(4, '0');
                    return {
                        id: item.id,
                        text: `Ficha: ${num}`
                    };
                })
            };
        }
    },
    minimumInputLength: 1
});
