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


def start(update, context):

    keyboard = [
        ['➡ Войти на сайт'],
        ['✉ Написать нам']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    update.message.reply_text(
        'Приветствуем!',
        reply_markup=reply_markup,
    )

    return States.MAIN


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


def get_api_respone(update, context):
    phone_number = update.message.contact.phone_number
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
        text = dedent('''
        📱 По вашему номеру не найдено регистрации.\n
        Ниже указаны ссылки на *регистрацию* и на 
        *прикрепление/смену номера* 👇\n
        _(ссылки действуют 5 мин)_''')

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton('Новая регистрация', url='https://www.yandex.ru')],
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
        text = f'Вот ссылка для входа на сайт\n_(действует 5 мин)_\n\n[{user_link}]({user_link})'
        update.message.reply_text(text, parse_mode='markdown')

    return main_menu(update, context)


def send_email(update, context):
    keyboard = [
        ['➡ Войти на сайт'],
        ['✉ Написать нам']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    update.message.reply_text(
        'Сделать функцию отправки письма',
        reply_markup=reply_markup,
    )

    return States.MAIN


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
                    level=logging.INFO)
    env = Env()
    env.read_env()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            States.MAIN: [
                MessageHandler(Filters.regex(r'^➡ Войти на сайт$'), phone_request),
                MessageHandler(Filters.regex(r'^✉ Написать нам$'), send_email),
            ],
            States.REQUEST: [
                CallbackQueryHandler(main_menu, pattern=r'^Завершить$'),
                MessageHandler(Filters.contact, get_api_respone),
                MessageHandler(Filters.regex(r'^Гостевая ссылка (без входа)$'), main_menu),
                MessageHandler(Filters.regex(r'^Отмена$'), main_menu),
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    while True:
        try:
            updater = Updater(token=env.str('TG_BOT_TOKEN'))
            dp = updater.dispatcher
            dp.add_handler(conv_handler)
            dp.add_error_handler(error)
            dp.bot_data = {
                'api_url': env.str('API_URL'),
            }
            updater.start_polling()
            updater.idle()
        except Exception:
            logger.exception('Ошибка в simple-reg-bot. Перезапуск через 5 секунд.')
            sleep(5)


if __name__ == '__main__':
    main()