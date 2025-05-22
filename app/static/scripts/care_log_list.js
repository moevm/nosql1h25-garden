document.addEventListener('DOMContentLoaded', function() {
    const gardenFilterSelect = document.getElementById('filter_garden_id');
    const bedFilterSelect = document.getElementById('filter_bed_id');
    
    if (gardenFilterSelect && bedFilterSelect) {
        const initialBedOptions = Array.from(bedFilterSelect.options);
        bedFilterSelect.dataset.selectedValue = "{{ filters.bed_id if filters and filters.bed_id else '' }}";

        gardenFilterSelect.addEventListener('change', function() {
            const gardenId = this.value;
            while (bedFilterSelect.options.length > 1) {
                bedFilterSelect.remove(1);
            }
            bedFilterSelect.dataset.selectedValue = ""; // Reset selected bed when garden changes

            if (gardenId) {
                fetch(`{{ url_for('care_bp.beds_for_dropdown', garden_id='PLACEHOLDER') }}`.replace('PLACEHOLDER', gardenId))
                    .then(response => response.json())
                    .then(data => {
                        if (data.error) {
                            console.error('Error fetching beds:', data.error);
                            return;
                        }
                        data.forEach(bed => {
                            const option = new Option(bed.name, bed.id);
                            bedFilterSelect.add(option);
                        });
                    })
                    .catch(error => console.error('Error fetching beds:', error));
            } 
        });
         // If a garden is pre-selected (e.g. from query params), populate its beds
        if (gardenFilterSelect.value && bedFilterSelect.dataset.selectedValue) {
             fetch(`{{ url_for('care_bp.beds_for_dropdown', garden_id='PLACEHOLDER') }}`.replace('PLACEHOLDER', gardenFilterSelect.value))
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        console.error('Error fetching beds:', data.error);
                        return;
                    }
                    while (bedFilterSelect.options.length > 1) { bedFilterSelect.remove(1); }
                    data.forEach(bed => {
                        const option = new Option(bed.name, bed.id);
                        if (bed.id === bedFilterSelect.dataset.selectedValue) {
                            option.selected = true;
                        }
                        bedFilterSelect.add(option);
                    });
                }).catch(error => console.error('Error fetching beds:', error));
        }
    }
});