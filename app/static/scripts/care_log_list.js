
document.addEventListener('DOMContentLoaded', function() {
    const gardenFilterSelect = document.getElementById('filter_garden_id');
    const bedFilterSelect = document.getElementById('filter_bed_id');
    
    if (gardenFilterSelect && bedFilterSelect) {
        const initialBedOptions = Array.from(bedFilterSelect.options);
        const selectedBedId = bedFilterSelect.dataset.selectedValue || '';

        gardenFilterSelect.addEventListener('change', function() {
            const gardenId = this.value;
            while (bedFilterSelect.options.length > 1) {
                bedFilterSelect.remove(1);
            }
            bedFilterSelect.selectedIndex = 0; // Reset selected bed when garden changes

            if (gardenId) {
                const bedsUrl = bedFilterSelect.dataset.bedsUrl.replace('PLACEHOLDER', gardenId);
                
                fetch(bedsUrl)
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
        if (gardenFilterSelect.value && selectedBedId) {
            const bedsUrl = bedFilterSelect.dataset.bedsUrl.replace('PLACEHOLDER', gardenFilterSelect.value);
            
            fetch(bedsUrl)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        console.error('Error fetching beds:', data.error);
                        return;
                    }
                    while (bedFilterSelect.options.length > 1) { 
                        bedFilterSelect.remove(1); 
                    }
                    data.forEach(bed => {
                        const option = new Option(bed.name, bed.id);
                        if (bed.id === selectedBedId) {
                            option.selected = true;
                        }
                        bedFilterSelect.add(option);
                    });
                }).catch(error => console.error('Error fetching beds:', error));
        }
    }
});