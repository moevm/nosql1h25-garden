document.addEventListener('DOMContentLoaded', function () {
    const btn = document.getElementById('hothouse-toggle');
    const hiddenInput = document.getElementById('is_hothouse');

    if (btn && hiddenInput) {
        btn.addEventListener('click', function () {
            const isActive = btn.classList.toggle('active');
            hiddenInput.value = isActive ? '1' : '0';
        });
    }
});