/**
 * Diacritical Mappings Management
 * JavaScript module for managing diacritical mappings
 */

// Main module for mappings management
const MappingsManager = (function() {
    // Private variables
    let mappingsTable;
    let deleteId = null;
    let selectedRows = [];
    
    // Initialize DataTable
    function initializeTable() {
        mappingsTable = $('#mappingsTable').DataTable({
            ajax: {
                url: '/api/mappings',
                dataSrc: ''
            },
            columns: [
                {
                    data: null,
                    defaultContent: '',
                    orderable: false,
                    className: 'select-checkbox'
                },
                { data: 'id' },
                { data: 'plain_text' },
                { data: 'diacritic_text' },
                { 
                    data: 'created_at',
                    render: function(data) {
                        return new Date(data).toLocaleString();
                    }
                },
                { 
                    data: 'updated_at',
                    render: function(data) {
                        return new Date(data).toLocaleString();
                    }
                },
                {
                    data: null,
                    className: 'action-buttons',
                    orderable: false,
                    render: function(data) {
                        return `
                            <button class="btn btn-sm btn-primary edit-btn" data-id="${data.id}">Edit</button>
                            <button class="btn btn-sm btn-danger delete-btn" data-id="${data.id}">Delete</button>
                        `;
                    }
                }
            ],
            order: [[1, 'asc']],
            select: {
                style: 'multi',
                selector: 'td:first-child'
            },
            pageLength: 10,
            lengthMenu: [10, 25, 50, 100]
        });
        
        // Handle row selection
        mappingsTable.on('select', function() {
            selectedRows = mappingsTable.rows({ selected: true }).data().toArray();
            updateSelectedCount();
        });
        
        mappingsTable.on('deselect', function() {
            selectedRows = mappingsTable.rows({ selected: true }).data().toArray();
            updateSelectedCount();
        });
        
        // Handle page length change
        $('#pageLengthSelect').on('change', function() {
            const newLength = parseInt($(this).val(), 10);
            mappingsTable.page.len(newLength).draw();
        });
    }
    
    // Update selected count and button state
    function updateSelectedCount() {
        const count = selectedRows.length;
        $('#selectedCount').text(`(${count} item${count !== 1 ? 's' : ''} selected)`);
        $('#batchDeleteBtn').prop('disabled', count === 0);
    }
    
    // Show alert message
    function showAlert(message, type = 'success') {
        const alertHtml = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="close" data-dismiss="alert" aria-label="Close">
                    <span aria-hidden="true">&times;</span>
                </button>
            </div>
        `;
        $('#alerts').html(alertHtml);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            $('.alert').alert('close');
        }, 5000);
    }
    
    // Add new mapping
    function setupAddMappingForm() {
        $('#mappingForm').on('submit', function(e) {
            e.preventDefault();
            
            const plainText = $('#plainText').val().trim();
            const diacriticText = $('#diacriticText').val().trim();
            
            $.ajax({
                url: '/api/mappings',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    plain_text: plainText,
                    diacritic_text: diacriticText
                }),
                success: function(response) {
                    showAlert('Mapping added successfully!');
                    $('#mappingForm')[0].reset();
                    mappingsTable.ajax.reload();
                },
                error: function(xhr) {
                    const error = xhr.responseJSON ? xhr.responseJSON.error : 'An error occurred';
                    showAlert(error, 'danger');
                }
            });
        });
    }
    
    // Edit mapping functionality
    function setupEditMapping() {
        // Open edit modal
        $('#mappingsTable').on('click', '.edit-btn', function() {
            const id = $(this).data('id');
            const row = mappingsTable.row($(this).closest('tr')).data();
            
            $('#editId').val(id);
            $('#editPlainText').val(row.plain_text);
            $('#editDiacriticText').val(row.diacritic_text);
            
            $('#editModal').modal('show');
        });
        
        // Save edited mapping
        $('#saveEdit').on('click', function() {
            const id = $('#editId').val();
            const plainText = $('#editPlainText').val().trim();
            const diacriticText = $('#editDiacriticText').val().trim();
            
            $.ajax({
                url: `/api/mappings/${id}`,
                method: 'PUT',
                contentType: 'application/json',
                data: JSON.stringify({
                    plain_text: plainText,
                    diacritic_text: diacriticText
                }),
                success: function(response) {
                    $('#editModal').modal('hide');
                    showAlert('Mapping updated successfully!');
                    mappingsTable.ajax.reload();
                },
                error: function(xhr) {
                    const error = xhr.responseJSON ? xhr.responseJSON.error : 'An error occurred';
                    showAlert(error, 'danger');
                }
            });
        });
    }
    
    // Delete mapping functionality
    function setupDeleteMapping() {
        // Open delete confirmation modal
        $('#mappingsTable').on('click', '.delete-btn', function() {
            const id = $(this).data('id');
            const row = mappingsTable.row($(this).closest('tr')).data();
            
            deleteId = id;
            $('#deletePlainText').text(row.plain_text);
            $('#deleteDiacriticText').text(row.diacritic_text);
            
            $('#deleteModal').modal('show');
        });
        
        // Confirm delete mapping
        $('#confirmDelete').on('click', function() {
            if (!deleteId) return;
            
            $.ajax({
                url: `/api/mappings/${deleteId}`,
                method: 'DELETE',
                success: function() {
                    $('#deleteModal').modal('hide');
                    showAlert('Mapping deleted successfully!');
                    mappingsTable.ajax.reload();
                },
                error: function(xhr) {
                    $('#deleteModal').modal('hide');
                    const error = xhr.responseJSON ? xhr.responseJSON.error : 'An error occurred';
                    showAlert(error, 'danger');
                }
            });
        });
    }
    
    // Batch delete functionality
    function setupBatchDelete() {
        // Open batch delete confirmation modal
        $('#batchDeleteBtn').on('click', function() {
            const count = selectedRows.length;
            if (count === 0) return;
            
            $('#deleteCount').text(count);
            $('#batchDeleteModal').modal('show');
        });
        
        // Confirm batch delete
        $('#confirmBatchDelete').on('click', function() {
            if (selectedRows.length === 0) return;
            
            const ids = selectedRows.map(row => row.id);
            
            $.ajax({
                url: '/api/mappings/batch-delete',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ ids: ids }),
                success: function(response) {
                    $('#batchDeleteModal').modal('hide');
                    showAlert(`Successfully deleted ${response.deleted_count} mappings!`);
                    mappingsTable.ajax.reload();
                    selectedRows = [];
                    updateSelectedCount();
                },
                error: function(xhr) {
                    $('#batchDeleteModal').modal('hide');
                    const error = xhr.responseJSON ? xhr.responseJSON.error : 'An error occurred';
                    showAlert(error, 'danger');
                }
            });
        });
    }
    
    // File upload functionality
    function setupFileUpload() {
        $('#uploadForm').on('submit', function(e) {
            e.preventDefault();
            
            const fileInput = document.getElementById('mappingsFile');
            if (!fileInput.files.length) {
                showAlert('Please select a file to upload', 'danger');
                return;
            }
            
            const file = fileInput.files[0];
            const importMode = $('input[name="importMode"]:checked').val();
            
            const formData = new FormData();
            formData.append('file', file);
            formData.append('mode', importMode);
            
            // Show progress and status
            $('#uploadProgress').show();
            $('#uploadStatus').html('<p class="text-info">Uploading file...</p>');
            
            $.ajax({
                url: '/api/mappings/upload',
                method: 'POST',
                data: formData,
                contentType: false,
                processData: false,
                success: function(response) {
                    $('#uploadProgress').hide();
                    $('#uploadStatus').html(`<p class="text-success">File processed successfully!</p>`);
                    
                    let message = '';
                    if (importMode === 'update') {
                        message = `Added ${response.added} new mappings, ${response.updated} updated.`;
                    } else {
                        message = `Database reset with ${response.total} mappings.`;
                    }
                    
                    showAlert(message);
                    mappingsTable.ajax.reload();
                    $('#uploadForm')[0].reset();
                },
                error: function(xhr) {
                    $('#uploadProgress').hide();
                    $('#uploadStatus').html(`<p class="text-danger">Upload failed. Please try again.</p>`);
                    const error = xhr.responseJSON ? xhr.responseJSON.error : 'An error occurred';
                    showAlert(error, 'danger');
                }
            });
        });
    }
    
    // Public methods
    return {
        init: function() {
            initializeTable();
            setupAddMappingForm();
            setupEditMapping();
            setupDeleteMapping();
            setupBatchDelete();
            setupFileUpload();
        },
        refreshTable: function() {
            if (mappingsTable) {
                mappingsTable.ajax.reload();
            }
        },
        showAlert: showAlert
    };
})();

// Initialize when document is ready
$(document).ready(function() {
    MappingsManager.init();
}); 