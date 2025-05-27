// Валидация даты и времени для форм рекомендаций
document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('form');
    const dueDateInput = document.getElementById('due_date');
    const dueTimeInput = document.getElementById('due_time');
    
    // Проверить, что элементы существуют на странице
    if (!dueDateInput || !dueTimeInput || !form) {
        return;
    }
    
    // Установить минимальную дату на сегодня
    const today = new Date().toISOString().split('T')[0];
    dueDateInput.setAttribute('min', today);
    
    // Валидация при отправке формы
    form.addEventListener('submit', function(e) {
        const dueDate = dueDateInput.value;
        const dueTime = dueTimeInput.value;
        
        if (dueDate && dueTime) {
            const dueDatetime = new Date(dueDate + 'T' + dueTime);
            const now = new Date();
            
            if (dueDatetime < now) {
                e.preventDefault();
                alert('Дата и время выполнения не могут быть в прошлом!');
                return false;
            }
        }
    });
    
    // Проверка при изменении даты
    dueDateInput.addEventListener('change', function() {
        const selectedDate = this.value;
        const today = new Date().toISOString().split('T')[0];
        
        if (selectedDate === today) {
            // Если выбрана сегодняшняя дата, установить минимальное время на текущее
            const now = new Date();
            const currentTime = now.getHours().toString().padStart(2, '0') + ':' + 
                              now.getMinutes().toString().padStart(2, '0');
            dueTimeInput.setAttribute('min', currentTime);
        } else {
            // Для будущих дат убрать ограничение по времени
            dueTimeInput.removeAttribute('min');
        }
    });
    
    // Проверка при изменении времени (дополнительная валидация)
    dueTimeInput.addEventListener('change', function() {
        const selectedDate = dueDateInput.value;
        const selectedTime = this.value;
        const today = new Date().toISOString().split('T')[0];
        
        if (selectedDate === today && selectedTime) {
            const now = new Date();
            const currentTime = now.getHours().toString().padStart(2, '0') + ':' + 
                              now.getMinutes().toString().padStart(2, '0');
            
            if (selectedTime < currentTime) {
                alert('Время не может быть в прошлом для сегодняшней даты!');
                this.value = currentTime;
            }
        }
    });
});