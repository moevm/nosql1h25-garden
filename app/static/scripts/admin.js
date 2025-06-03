// Handle delete confirmations
document.addEventListener('DOMContentLoaded', function() {
    const deleteButtons = document.querySelectorAll('[data-action="delete"]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const itemId = this.closest('tr').dataset.itemId;
            const itemType = this.closest('table').dataset.itemType;
            const itemName = this.closest('tr').querySelector('td').textContent.trim();
            
            if (confirm(`Are you sure you want to delete this ${itemType.slice(0, -1)}? This action cannot be undone.\n\nItem: ${itemName}`)) {
                // Create a form to submit the delete request
                const form = document.createElement('form');
                form.method = 'POST';
                form.action = `/admin/${itemType}/${itemId}/delete`;
                document.body.appendChild(form);
                form.submit();
            }
        });
    });
});

// Handle date range validation
function validateDateRange() {
    const dateFrom = document.querySelector('input[name="date_from"]');
    const dateTo = document.querySelector('input[name="date_to"]');
    
    if (dateFrom && dateTo) {
        dateTo.addEventListener('change', function() {
            if (dateFrom.value && this.value && this.value < dateFrom.value) {
                alert('End date must be after start date');
                this.value = '';
            }
        });
        
        dateFrom.addEventListener('change', function() {
            if (dateTo.value && this.value && dateTo.value < this.value) {
                alert('Start date must be before end date');
                this.value = '';
            }
        });
    }
}

// Handle clear filters
function clearFilters() {
    const clearButtons = document.querySelectorAll('[data-action="clear-filters"]');
    clearButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const form = this.closest('form');
            const inputs = form.querySelectorAll('input, select');
            inputs.forEach(input => {
                input.value = '';
            });
            form.submit();
        });
    });
}

// Handle table row actions
function initializeTableActions() {
    // View details
    document.querySelectorAll('[data-action="view"]').forEach(button => {
        button.addEventListener('click', function() {
            const itemId = this.closest('tr').dataset.itemId;
            const itemType = this.closest('table').dataset.itemType;
            window.location.href = `/admin/${itemType}/${itemId}`;
        });
    });

    // Edit item
    document.querySelectorAll('[data-action="edit"]').forEach(button => {
        button.addEventListener('click', function() {
            const itemId = this.closest('tr').dataset.itemId;
            const itemType = this.closest('table').dataset.itemType;
            window.location.href = `/admin/${itemType}/${itemId}/edit`;
        });
    });
}

// Initialize all functionality
document.addEventListener('DOMContentLoaded', function() {
    validateDateRange();
    clearFilters();
    initializeTableActions();
}); 