from datetime import datetime
from email.policy import default
from textwrap import dedent

import requests
from enum import Enum, auto
from environs import Env
from time import sleep
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackQueryHandler

import logging

logger = logging.getLogger(__name__)


class States(Enum):
    MAIN = auto()
    REQUEST = auto()
    WRITE_TO_US = auto()
    MESSAGE_TO_ADMIN = auto()


def phone_request(update, context):
    keyboard = [
        [KeyboardButton('Отправить номер телефона', request_contact=True)],
        ['Гостевая ссылка (без входа)', 'Отмена'],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    update.message.reply_text(
        'Чтобы войти или зарегистрироваться на сайте, нужно предоставить номер',
        reply_markup=reply_markup,
    )

    return States.REQUEST


def main_menu(update, context):
    keyboard = [
        ['➡ Войти на сайт'],
        ['✉ Написать нам']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    context.bot.send_message(
        text='Главное меню. Выберете действие!',
        chat_id=update.effective_chat.id,
        reply_markup=reply_markup,
    )

    return States.MAIN


def start(update, context):
    if not 'phone_number' in context.user_data:
        return phone_request(update, context)
    return main_menu(update, context)


def get_api_respone(update, context):
    phone_number = context.user_data['phone_number']
    chat_id = update.message.chat_id
    username = update.message.chat.username

    api_url = context.bot_data['api_url']
    payload = {
         'phone': phone_number,
         'chat_id': chat_id,
         'username': username
    }
    response = requests.post(api_url, data=payload)
    response.raise_for_status()
    user_status = response.json()
    if 'register' in user_status:
        user_link = user_status['register']
        text = dedent('''
            📱 По вашему номеру не найдено регистрации.\n
            Ниже указаны ссылки на *регистрацию* и на 
            *прикрепление/смену номера* 👇\n
            _(ссылки действуют 5 мин)_'''
        )
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton('Новая регистрация', url='https://ya.ru')],
                             [InlineKeyboardButton('Завершить', callback_data='Завершить')]]
        )
        update.message.reply_text(
            text,
            parse_mode='markdown',
            reply_markup=reply_markup,
        )
        return States.REQUEST
    elif 'login' in user_status:
        user_link = user_status['login']
        text = f'Вот ссылка для входа на сайт\n_(действует 5 мин_\n\n[{user_link}](https://ya.ru)'
        update.message.reply_text(text, parse_mode='markdown')

    return main_menu(update, context)


def get_guest_link(update, context):
    api_guest_url = context.bot_data['api_guest_url']
    response = requests.get(api_guest_url)
    guest_url = response.json()['url']
    text = f'Вот гостевая ссылка для входа на сайт\n_(действует 5 мин_\n\n[{guest_url}]({guest_url})'
    update.message.reply_text(text, parse_mode='markdown')

    return start(update, context)


def handle_new_phonenumber(update, context):
    context.user_data['phone_number'] = update.message.contact.phone_number
    return get_api_respone(update, context)


def write_to_us(update, context):
    text ='Внимательно выберите тему обращения:'
    reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton('Предложение партнерства', callback_data='Предложение партнерства'),
                InlineKeyboardButton('Активировать кабинет', callback_data='Активировать кабинет')
            ],
            [
                InlineKeyboardButton('Забыл(а) пароль', callback_data='Забыл(а) пароль'),
                InlineKeyboardButton('Другое', callback_data='Другое')
            ],
        ],
    )
    update.message.reply_text(
        text,
        parse_mode='markdown',
        reply_markup=reply_markup,
    )
    return States.WRITE_TO_US


def choose_topic(update, context):
    topic = update.callback_query.data
    context.user_data['topic'] = topic
    keyboard = [
        ['➡ Войти на сайт'],
        ['✉ Написать нам']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    context.bot.send_message(
        text=f'Тема: {topic}\nВведите текст вашего обращения:',
        chat_id=update.effective_chat.id,
        parse_mode='markdown',
        reply_markup=reply_markup,
    )

    return States.MESSAGE_TO_ADMIN



def send_message_to_admin(update, context):
    if not 'phone_number' in context.user_data:
        phone = 'Не указан'
    else:
        phone = context.user_data['phone_number']
    topic = context.user_data['topic']

    message = dedent(f'''
        Дата и время: {str(datetime.now())}
        chat id: {update.message.chat_id}
        username: {update.message.chat.username}
        phone: {phone}
        Тема: {topic}
        Текст сообщения: {update.message.text}'''
    )

    if context.bot_data['admin_chat_id']:
        context.bot.send_message(
            text=message,
            chat_id=context.bot_data['admin_chat_id'],
        )

    update.message.reply_text('Сообщение отослано.')
    return start(update, context)


def cancel(update, context):
    username = update.effective_user.first_name
    logger.info(f'User {username} canceled the conversation.')
    update.message.reply_text('До встречи!',
                              reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


def error(update, error):
    """Log Errors caused by Updates."""
    logger.warning(f'Update "{update}" caused error "{error}"')


def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)
    env = Env()
    env.read_env()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            States.MAIN: [
                MessageHandler(Filters.regex(r'^➡ Войти на сайт$'), get_api_respone),
                MessageHandler(Filters.regex(r'^✉ Написать нам$'), write_to_us),
            ],
            States.REQUEST: [
                MessageHandler(Filters.regex(r'^➡ Войти на сайт$'), get_api_respone),
                MessageHandler(Filters.regex(r'^✉ Написать нам$'), write_to_us),
                CallbackQueryHandler(start, pattern=r'^Завершить$'),
                MessageHandler(Filters.contact, handle_new_phonenumber),
                MessageHandler(Filters.regex(r'^Гостевая ссылка'), get_guest_link),
                MessageHandler(Filters.regex(r'^Отмена$'), start),
            ],
            States.WRITE_TO_US: [
                CallbackQueryHandler(choose_topic),
                MessageHandler(Filters.regex(r'^➡ Войти на сайт$'), get_api_respone),
                MessageHandler(Filters.regex(r'^✉ Написать нам$'), write_to_us),
            ],
            States.MESSAGE_TO_ADMIN: [
                MessageHandler(Filters.regex(r'^➡ Войти на сайт$'), get_api_respone),
                MessageHandler(Filters.regex(r'^✉ Написать нам$'), write_to_us),
                MessageHandler(Filters.text, send_message_to_admin),
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True,
    )

    while True:
        try:
            updater = Updater(token=env.str('TG_BOT_TOKEN'))
            dp = updater.dispatcher
            dp.add_handler(conv_handler)
            dp.add_error_handler(error)
            dp.bot_data = {
                'api_url': env.str('API_URL'),
                'api_guest_url': env.str('API_GUEST_URL'),
                'admin_chat_id': env.str('ADMIN_CHAT_ID', default=None)
            }
            updater.start_polling()
            updater.idle()
        except Exception:
            logger.exception('Ошибка в simple-reg-bot. Перезапуск через 5 секунд.')
            sleep(5)


if __name__ == '__main__':
    main()