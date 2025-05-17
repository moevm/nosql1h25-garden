const addSectionBtn = document.querySelector('.add-section-btn');
const sectionsList = document.querySelector('.sections-list');


function addSection(name) {
    const sectionItem = document.createElement('div');
    sectionItem.classList.add('section-item');

    const sectionName = document.createElement('span');
    sectionName.classList.add('section-name');
    sectionName.textContent = name;

    const sectionDate = document.createElement('span');
    sectionDate.classList.add('section-date');
    sectionDate.textContent = new Date().toLocaleString();

    const actions = document.createElement('div');
    actions.classList.add('actions');

    const editIcon = document.createElement('button');
    editIcon.classList.add('edit-button');
    editIcon.alt = 'Редактировать';
    editIcon.style.cursor = 'pointer';

    const deleteIcon = document.createElement('button');
    deleteIcon.classList.add('delete-button');
    deleteIcon.alt = 'Удалить';
    deleteIcon.style.cursor = 'pointer';

    deleteIcon.addEventListener('click', () => {
        if (confirm('Вы действительно хотите удалить этот участок?')) {
            sectionsList.removeChild(sectionItem);
        }
    });

    actions.appendChild(editIcon);
    actions.appendChild(deleteIcon);

    sectionItem.appendChild(sectionName);
    sectionItem.appendChild(sectionDate);
    sectionItem.appendChild(actions);

    sectionsList.appendChild(sectionItem);
}

addSectionBtn.addEventListener('click', () => {
    const newName = prompt('Введите название участка:');
    if (newName && newName.trim() !== '') {
        addSection(newName);
    }
});
