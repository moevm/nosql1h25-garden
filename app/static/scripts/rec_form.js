document.addEventListener('DOMContentLoaded', function() {
    const gardenSelect = document.getElementById('garden_id');
    const bedSelect = document.getElementById('bed_id');
    
    function populateBeds(gardenId, selectedBedId) {
        if (!gardenId) {
            while (bedSelect.options.length > 1) {
                bedSelect.remove(1);
            }
            bedSelect.options[0].text = "-- Сначала выберите участок --";
            bedSelect.disabled = true;
            return;
        }
        
        bedSelect.disabled = true;
        bedSelect.options[0].text = "Загрузка...";
        
        // Fetch beds for selected garden
        const bedsUrl = bedSelect.dataset.bedsUrl.replace('GARDEN_ID', gardenId);
        
        fetch(bedsUrl)
            .then(response => response.json())
            .then(data => {
                while (bedSelect.options.length > 1) {
                    bedSelect.remove(1);
                }
                
                if (data.error) {
                    bedSelect.options[0].text = "Ошибка загрузки грядок";
                    console.error(data.error);
                    return;
                }
                
                if (data.length === 0) {
                    bedSelect.options[0].text = "Нет грядок для этого участка";
                    return;
                }
                
                bedSelect.options[0].text = "-- Выберите грядку --";
                data.forEach(bed => {
                    const option = document.createElement('option');
                    option.value = bed.id;
                    option.textContent = bed.name;
                    if (bed.id === selectedBedId) {
                        option.selected = true;
                    }
                    bedSelect.appendChild(option);
                });
                
                bedSelect.disabled = false;
            })
            .catch(error => {
                console.error('Error fetching beds:', error);
                bedSelect.options[0].text = "Ошибка загрузки грядок";
            });
    }
    
    gardenSelect.addEventListener('change', function() {
        populateBeds(this.value);
    });
    
    // Initial population if garden is selected
    if (gardenSelect.value) {
        const initialBedId = bedSelect.dataset.initialBedId || '';
        populateBeds(gardenSelect.value, initialBedId);
    }
});