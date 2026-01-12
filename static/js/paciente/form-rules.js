// static/js/paciente/form-rules.js

(function () {

    const el = {
        rut: document.getElementById('id_rut'),
        nip: document.getElementById('id_nip'),
        pasaporte: document.getElementById('id_pasaporte'),
        rut_resp: document.getElementById('id_rut_responsable_temporal'),
        rut_madre: document.getElementById('id_rut_madre'),
        fecha_fallecimiento: document.getElementById('id_fecha_fallecimiento'),
        ocupacion: document.getElementById('id_ocupacion'),
        nombre_pareja: document.getElementById('id_nombre_pareja'),
        telefono1: document.getElementById('id_numero_telefono1'),
        telefono2: document.getElementById('id_numero_telefono2'),

        recien_nacido: document.getElementById('id_recien_nacido'),
        extranjero: document.getElementById('id_extranjero'),
        fallecido: document.getElementById('id_fallecido'),
        sin_telefono: document.getElementById('id_sin_telefono'),
        usar_rut_madre: document.getElementById('id_usar_rut_madre_como_responsable'),
    };

    function disable(fields) {
        fields.forEach(f => {
            if (!f) return;
            f.disabled = true;
            f.removeAttribute('required');
        });
    }

    function enable(fields) {
        fields.forEach(f => {
            if (!f) return;
            f.disabled = false;
        });
    }

    function applyRules() {

        const rn = el.recien_nacido.checked;
        const ext = el.extranjero.checked;
        const fal = el.fallecido.checked;
        const sn = el.sin_telefono.checked;

        enable([
            el.rut, el.nip, el.pasaporte, el.rut_resp, el.rut_madre,
            el.fecha_fallecimiento, el.ocupacion, el.nombre_pareja,
            el.telefono1, el.telefono2
        ]);

        // ESTÁNDAR
        if (!rn && !ext && !fal) {
            disable([el.nip, el.pasaporte, el.rut_resp, el.fecha_fallecimiento]);
            el.usar_rut_madre.checked = false;
            el.rut.required = true;
        }

        // FALLECIDO
        if (!rn && !ext && fal) {
            disable([el.nip, el.pasaporte, el.rut_resp]);
            el.fecha_fallecimiento.required = true;
            el.rut.required = true;
        }

        // RN
        if (rn && !ext && !fal) {
            disable([el.nip, el.pasaporte, el.ocupacion, el.nombre_pareja, el.fecha_fallecimiento]);
        }

        // RN + FALLECIDO
        if (rn && !ext && fal) {
            disable([el.nip, el.pasaporte, el.ocupacion, el.nombre_pareja]);
            el.fecha_fallecimiento.required = true;
            el.rut.disabled = true;
        }

        // EXTRANJERO
        if (!rn && ext && !fal) {
            disable([el.rut_resp, el.fecha_fallecimiento]);
        }

        // EXTRANJERO + FALLECIDO
        if (!rn && ext && fal) {
            disable([el.rut_resp]);
            el.fecha_fallecimiento.required = true;
        }

        // RN + EXTRANJERO
        if (rn && ext && !fal) {
            disable([el.rut, el.ocupacion, el.nombre_pareja, el.fecha_fallecimiento]);
        }

        // RN + EXTRANJERO + FALLECIDO
        if (rn && ext && fal) {
            disable([el.rut, el.ocupacion, el.nombre_pareja]);
            el.fecha_fallecimiento.required = true;
        }

        // TELÉFONOS
        if (sn) {
            disable([el.telefono1, el.telefono2]);
        } else {
            enable([el.telefono1, el.telefono2]);
            el.telefono1.required = true;
        }
    }

    document.addEventListener('change', e => {
        if (!e.target) return;
        if (['id_recien_nacido', 'id_extranjero', 'id_fallecido', 'id_sin_telefono'].includes(e.target.id)) {
            applyRules();
        }
    });

    document.addEventListener('DOMContentLoaded', applyRules);
    window.actualizarReglasPaciente = applyRules;

})();
