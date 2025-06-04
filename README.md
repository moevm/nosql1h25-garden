# nosql_template


## Предварительная проверка заданий

<a href=" ./../../../actions/workflows/1_helloworld.yml" >![1. Согласована и сформулирована тема курсовой]( ./../../actions/workflows/1_helloworld.yml/badge.svg)</a>

<a href=" ./../../../actions/workflows/2_usecase.yml" >![2. Usecase]( ./../../actions/workflows/2_usecase.yml/badge.svg)</a>

<a href=" ./../../../actions/workflows/3_data_model.yml" >![3. Модель данных]( ./../../actions/workflows/3_data_model.yml/badge.svg)</a>

<a href=" ./../../../actions/workflows/4_prototype_store_and_view.yml" >![4. Прототип хранение и представление]( ./../../actions/workflows/4_prototype_store_and_view.yml/badge.svg)</a>

<a href=" ./../../../actions/workflows/5_prototype_analysis.yml" >![5. Прототип анализ]( ./../../actions/workflows/5_prototype_analysis.yml/badge.svg)</a> 

<a href=" ./../../../actions/workflows/6_report.yml" >![6. Пояснительная записка]( ./../../actions/workflows/6_report.yml/badge.svg)</a>

<a href=" ./../../../actions/workflows/7_app_is_ready.yml" >![7. App is ready]( ./../../actions/workflows/7_app_is_ready.yml/badge.svg)</a>

## Инструкция по запуску
Клонировать репозиторий:
```bash
git clone https://github.com/moevm/nosql1h25-garden.git
cd nosql1h25-garden/
```
Собрать и запустить проект:
```bash
docker-compose up --build
```
Проект будет доступен по адресу `localhost:5000/`

## Подготовленные пользователи
При запуске проекта, бд наполнится 3 пользователями, грядками, участками и др.

## Массовый импорт и экспорт
Массовый импорт и экспорт данных доступен для админа в админ-панели. Также, импорт и экспорт собственных данных доступен для обычного пользователя.

### Данные для входа за каждого из пользователей:
1. Admin (имеет доступ к адресам .../admin)

    **Логин**: admin@garden.com
  
    **Пароль**: admin123

2. Обычный пользователь (с заготовленными участками, грядками, записями об уходе)

    **Логин**: user1@garden.com
  
    **Пароль**: user123

3. Обычный пользователь 2 (с заготовленными участками, грядками, записями об уходе)

    **Логин**: user2@garden.com
  
    **Пароль**: user234

