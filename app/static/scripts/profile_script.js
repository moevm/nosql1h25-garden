const editButton = document.querySelector('.edit-name-button');
const nameText = document.querySelector('.name-text');
const nameInput = document.querySelector('.name-input');

editButton.addEventListener('click', () => {
  nameInput.style.display = 'inline-block';
  nameInput.value = nameText.textContent;
  nameText.style.display = 'none';
  nameInput.focus();
});

nameInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') {
    const newName = nameInput.value.trim();
    if (newName !== '') {
      nameText.textContent = newName;
    }
    nameInput.style.display = 'none';
    nameText.style.display = 'inline';
  }
});
