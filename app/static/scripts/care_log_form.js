document.addEventListener('DOMContentLoaded', function() {
    const gardenSelect = document.getElementById('garden_id');
    const bedSelect = document.getElementById('bed_id');
    const initialBedId = "{{ form_data.bed_id if form_data and form_data.bed_id else '' }}";

    function populateBeds(gardenId, selectedBedId) {
        while (bedSelect.options.length > 1) {
            bedSelect.remove(1);
        }
        if (!gardenId) {
            bedSelect.options[0].text = "-- Сначала выберите участок --";
            bedSelect.disabled = true;
            return;
        }

        bedSelect.disabled = false;
        bedSelect.options[0].text = "-- Загрузка грядок... --";

        fetch(`{{ url_for('care_bp.beds_for_dropdown', garden_id='PLACEHOLDER') }}`.replace('PLACEHOLDER', gardenId))
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                bedSelect.options[0].text = "-- Выберите грядку --";
                if (data.error) {
                    console.error('Error fetching beds:', data.error);
                     bedSelect.options[0].text = "-- Ошибка загрузки грядок --";
                    return;
                }
                if (data.length === 0) {
                    bedSelect.options[0].text = "-- Нет грядок на этом участке --";
                    return;
                }
                data.forEach(bed => {
                    const option = new Option(bed.name, bed.id);
                    if (bed.id === selectedBedId) {
                        option.selected = true;
                    }
                    bedSelect.add(option);
                });
            })
            .catch(error => {
                console.error('Error fetching beds:', error);
                bedSelect.options[0].text = "-- Ошибка загрузки грядок --";
            });
    }

    gardenSelect.addEventListener('change', function() {
        populateBeds(this.value, null); 
    });

    if (gardenSelect.value) {
        populateBeds(gardenSelect.value, initialBedId);
    } else {
        bedSelect.disabled = true; 
    }
});