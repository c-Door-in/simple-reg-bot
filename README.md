# simple-reg-bot
 Простой бот для проверки регистрации пользователя.  
 Посредством API запроса проверяет наличие пользователя в базе данных. 
 Возвращает полученную ссылку.
 API сервер должен принимать на проверку три значения, полученные с помощью POST запроса:
 - phone
 - chat_id
 - username

 ### Установка
 Уже должен быть установлен Python 3.  
 Склонируйте проект к себе.
 Для подключения зависимостей запустите команду:
 ```bash
 pip install -r requirements.txt
 ```
 В корне проекта создайте файл `.env`. В него положите следующие переменные:
 ```bash
 API_URL=<Адрес API сервера>

 API_GUEST_URL=<Адрес API для получение гостевой ссылки>

 TG_BOT_TOKEN=<Токен бота в Телеграм>

 ADMIN_CHAT_ID=<ID телеграм чата админа, который будет получать сообщения от пользователей>
 ```

 ### Запуск

 Команда запуска:
 ```bash
 python tg_bot.py
 ```
 В случае ошибки бота, выдается сообщение об ошибке в консоль, и бот перезапускается через 5 секунд.
