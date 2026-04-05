📱 Swillgram - Мессенджер с историями
Swillgram - это полнофункциональный веб-мессенджер с возможностью обмена сообщениями, файлами, аудио/видеозвонками, историями (аналог Stories) и многими другими функциями.

✨ Основные возможности
💬 Общение
Отправка текстовых сообщений

Обмен файлами (фото, видео, аудио, документы до 100 МБ)

Редактирование и удаление сообщений (в том числе "для всех")

Пересылка сообщений

Ответ на конкретное сообщение

Чат "Избранное" для сохранения важных заметок и файлов

📞 Звонки
Аудиозвонки

Видеозвонки (WebRTC)

Отключение микрофона и камеры во время звонка

История звонков

📸 Истории (Stories)
Публикация фото и видео историй

Добавление текста на историю

Добавление музыки к истории

Настройка приватности: все / только контакты / выбранные пользователи

Просмотр историй других пользователей

Лайки историй (только один раз от пользователя)

Ответы на истории (открывается чат с автором)

Просмотр списка пользователей, посмотревших историю

👤 Профиль и настройки
Редактирование профиля (имя, фото, описание, дата рождения)

Обрезка аватарки через Canvas

Ночная тема (автоматическое сохранение в БД)

Настройка размера шрифта

Настройка скругления сообщений

Настройки конфиденциальности (кто видит время захода, фото профиля, может звонить/писать)

🔐 Безопасность
Регистрация и вход по номеру телефона

Запоминание сессии ("Запомнить меня")

Управление активными сессиями (просмотр и завершение)

Хеширование паролей (SHA-256)

📱 Интерфейс
Адаптивный дизайн (работает на мобильных устройствах)

Бургер-меню в стиле Telegram

Контекстное меню для сообщений (правый клик)

Поиск пользователей по имени или номеру

Список контактов

Непрочитанные сообщения (красный кружок)

🛠 Технологии
Бэкенд
Flask - веб-фреймворк

Flask-SocketIO - WebSocket для реального времени

SQLite - база данных

WebRTC - аудио/видеозвонки

Pillow - обработка изображений

Фронтенд
HTML5 / CSS3 - адаптивная вёрстка

JavaScript (ES6) - клиентская логика

Canvas API - обрезка аватарок и редактирование историй

WebRTC - медиа-коммуникации

📁 Структура проекта
text
Swillgram/
├── main.py                 # Основной сервер (Flask + SocketIO)
├── swillgram.db            # База данных SQLite (создаётся автоматически)
├── static/
│   └── uploads/            # Загруженные файлы
│       ├── avatars/        # Аватарки пользователей
│       ├── photos/         # Фото в сообщениях
│       ├── videos/         # Видео в сообщениях
│       ├── audio/          # Аудио в сообщениях
│       ├── files/          # Документы
│       ├── stories/        # Медиа для историй
│       └── story_music/    # Музыка для историй
└── templates/
    ├── chat.html           # Главная страница мессенджера
    ├── login.html          # Страница входа
    └── register.html       # Страница регистрации
🚀 Установка и запуск
1. Клонирование репозитория
bash
git clone https://github.com/your-repo/Swillgram.git
cd Swillgram
2. Создание виртуального окружения
bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows
3. Установка зависимостей
bash
pip install flask flask-socketio pillow
4. Запуск приложения
bash
python main.py
5. Открытие в браузере
text
http://localhost:5000
📝 API Маршруты
Пользователи
Метод	Маршрут	Описание
GET	/api/search_users?q=	Поиск пользователей
GET	/api/get_user/<id>	Получить информацию о пользователе
GET	/api/get_my_user	Получить информацию о себе
POST	/api/update_profile	Обновить профиль
Контакты
Метод	Маршрут	Описание
GET	/api/get_contacts	Получить список контактов
POST	/api/add_contact	Добавить контакт
POST	/api/rename_contact	Переименовать контакт
Сообщения
Метод	Маршрут	Описание
GET	/api/get_chat/<user_id>	Получить чат с пользователем
POST	/api/send_message	Отправить сообщение
POST	/api/edit_message	Редактировать сообщение
POST	/api/delete_message	Удалить сообщение
POST	/api/forward_message	Переслать сообщение
Звонки
Метод	Маршрут	Описание
POST	/api/make_call	Совершить звонок
POST	/api/answer_call	Ответить на звонок
POST	/api/end_call	Завершить звонок
GET	/api/get_call_history	История звонков
Истории
Метод	Маршрут	Описание
GET	/api/get_stories	Получить истории
POST	/api/upload_story	Опубликовать историю
POST	/api/story_view	Зафиксировать просмотр
POST	/api/story_like	Поставить лайк
POST	/api/story_reply	Ответить на историю
GET	/api/get_story_viewers/<id>	Получить просмотревших
Настройки
Метод	Маршрут	Описание
GET	/api/get_settings	Получить настройки
POST	/api/update_theme	Обновить тему
POST	/api/update_font_size	Обновить размер шрифта
POST	/api/update_bubble_radius	Обновить скругление
GET	/api/get_privacy	Получить настройки приватности
POST	/api/update_privacy	Обновить приватность
Сессии
Метод	Маршрут	Описание
GET	/api/get_sessions	Получить активные сессии
POST	/api/terminate_session	Завершить сессию
POST	/api/terminate_all_sessions	Завершить все сессии
🗄️ Структура базы данных
users
id, phone, username, password, avatar, bio, birthday

last_seen, created_at

privacy_*, theme, font_size, bubble_radius, wallpaper

chats
id, user1_id, user2_id, created_at

messages
id, chat_id, sender_id, content, file_*, is_read, is_deleted, edited_at

contacts
user_id, contact_id

contact_names
user_id, contact_id, name (пользовательские имена)

favorites
user_id, file_*, note

calls
caller_id, receiver_id, call_type, status, duration

user_sessions
user_id, session_token, device, ip, last_active

stories
user_id, file_type, file_path, caption, music, expires_at

story_interactions
story_id, user_id, type (view/like/reply), reply_text

story_privacy
story_id, privacy_type (everyone/contacts/selected)

story_allowed_users
story_id, user_id

🎨 Особенности интерфейса
Адаптивность: при ширине экрана менее 768px сайдбар скрывается

Тёмная тема: переключение через бургер-меню, сохраняется в БД

Контекстное меню: правый клик на сообщении для дополнительных действий

WebRTC звонки: реальное время, переключение микрофона/камеры

⚠️ Известные ограничения
Максимальный размер загружаемого файла: 100 МБ (можно увеличить)

Видеозвонки требуют HTTPS в production (для локальной разработки HTTP работает)

Истории автоматически удаляются через 24 часа

Звук в историях не воспроизводится автоматически (требуется взаимодействие пользователя)

🔧 Устранение неполадок
Ошибка "duplicate column name"
Удалите файл swillgram.db и перезапустите сервер.

Истории не публикуются
Проверьте, что созданы папки static/uploads/stories и static/uploads/story_music.

WebRTC не работает
Убедитесь, что сайт открыт по HTTPS (для production) или используйте localhost для разработки.

Не меняются цвета в тёмной теме
Очистите кэш браузера (Ctrl+Shift+R) и перезагрузите страницу.

📄 Лицензия
MIT License

👨‍💻 Автор
Swillgram Team