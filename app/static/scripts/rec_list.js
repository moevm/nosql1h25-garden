document.addEventListener('DOMContentLoaded', function() {
    const gardenFilterSelect = document.getElementById('garden_id');
    const bedFilterSelect = document.getElementById('bed_id');
    
    if (gardenFilterSelect && bedFilterSelect) {
        // Store initial bed options
        const initialBedOptions = Array.from(bedFilterSelect.options);
        const selectedBedId = bedFilterSelect.dataset.selectedValue || '';

        gardenFilterSelect.addEventListener('change', function() {
            const gardenId = this.value;
            while (bedFilterSelect.options.length > 1) {
                bedFilterSelect.remove(1);
            }

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
                            if (bed.id === selectedBedId) {
                                option.selected = true;
                            }
                            bedFilterSelect.add(option);
                        });
                    })
                    .catch(error => console.error('Error fetching beds:', error));
            }
        });

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