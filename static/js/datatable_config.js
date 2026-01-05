document.addEventListener('DOMContentLoaded', function () {
    const sidebarWrapper = document.querySelector('.sidebar-wrapper');
    if (sidebarWrapper && OverlayScrollbarsGlobal?.OverlayScrollbars) {
        OverlayScrollbarsGlobal.OverlayScrollbars(sidebarWrapper, {
            scrollbars: {theme: 'os-theme-light', autoHide: 'leave', clickScroll: true}
        });
    }
});

$(document).ready(function () {
    $('#Table').DataTable({
        responsive: true,
        fixedHeader: true,
        lengthChange: true,
        autoWidth: true,
        dom:
            "<'row mb-2'<'col-sm-6'l><'col-sm-6'f>>" +
            "<'row'<'col-sm-12'tr>>" +
            "<'row mt-2'<'col-sm-4'i><'col-sm-4 text-center'B><'col-sm-4'p>>",
        buttons: [
            {extend: 'pdf', className: 'btn btn-secondary btn-sm'},
            {extend: 'print', className: 'btn btn-secondary btn-sm'}
        ],
        language: {
            url: datatableLangUrl,
            emptyTable: "No hay registros disponibles",
            paginate: {
                first: "&laquo;&laquo;",
                previous: "&laquo;",
                next: "&raquo;",
                last: "&raquo;&raquo;"
            }
        },
    });
});