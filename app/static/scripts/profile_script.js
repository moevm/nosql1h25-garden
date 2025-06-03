window.addEventListener('DOMContentLoaded', () => {
  // Auto-hide flash messages after 5 seconds
  const flashMessages = document.querySelectorAll('.flash-message');
  flashMessages.forEach(message => {
    setTimeout(() => {
      message.style.transition = 'opacity 0.5s ease-out';
      message.style.opacity = '0';
      setTimeout(() => {
        message.remove();
      }, 500); // Remove after fade out
    }, 5000); // 5 seconds
    // Обработка кнопок экспорта и импорта
  const exportBtn = document.querySelector('.export-btn');
  const importBtn = document.querySelector('.import-btn');

  if (exportBtn) {
    exportBtn.addEventListener('click', () => {
      // Пока заглушка - можно будет реализовать позже
      alert('Функция экспорта данных будет реализована в следующих версиях');
    });
  }

  if (importBtn) {
    importBtn.addEventListener('click', () => {
      // Пока заглушка - можно будет реализовать позже
      alert('Функция импорта данных будет реализована в следующих версиях');
    });
  }
});

  const avatarContainer = document.getElementById('avatar-container');
  const photoInput = document.getElementById('photo-input');
  const profileForm = document.getElementById('profile-form');
  const avatarImg = document.getElementById('avatar-img');

  // Обработка клика по аватару для выбора фото
  avatarContainer.addEventListener('click', () => {
    photoInput.click();
  });

  // Обработка изменения фото
  photoInput.addEventListener('change', (e) => {
    if (photoInput.files.length > 0) {
      const file = photoInput.files[0];
      
      // Проверяем, что файл является изображением
      if (!file.type.startsWith('image/')) {
        alert('Пожалуйста, выберите файл изображения');
        photoInput.value = '';
        return;
      }
      
      // Показываем превью нового изображения
      const reader = new FileReader();
      reader.onload = (e) => {
        avatarImg.src = e.target.result;
      };
      reader.readAsDataURL(file);
      
      // Отправляем форму для сохранения
      profileForm.submit();
    }
  });

  // Обработка редактирования имени
  const editNameBtn = document.getElementById('edit-name-button');
  const saveNameBtn = document.getElementById('save-name-button');
  const nameText = document.getElementById('name-text');
  const nameInput = document.getElementById('name-input');

  if (editNameBtn && saveNameBtn && nameText && nameInput) {
    editNameBtn.addEventListener('click', () => {
      nameText.hidden = true;
      editNameBtn.hidden = true;
      nameInput.hidden = false;
      saveNameBtn.hidden = false;
      nameInput.focus();
      nameInput.select(); // Выделяем весь текст для удобного редактирования
    });

    // Сохранение по Enter
    nameInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        profileForm.submit();
      }
    });

    // Отмена редактирования по Escape
    nameInput.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        nameInput.value = nameText.textContent; // Возвращаем исходное значение
        nameText.hidden = false;
        editNameBtn.hidden = false;
        nameInput.hidden = true;
        saveNameBtn.hidden = true;
      }
    });
  }
});


document.addEventListener('DOMContentLoaded', function() {
  const exportLink = document.getElementById('export-data-link');
  if (exportLink) {
    exportLink.addEventListener('click', function(event) {
      event.preventDefault();

      // Создаем и отправляем POST-запрос через временную форму
      const form = document.createElement('form');
      form.method = 'POST';
      form.action = exportLink.dataset.exportUrl;
      document.body.appendChild(form);
      form.submit();
    });
  }
});
