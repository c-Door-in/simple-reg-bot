import requests
from enum import Enum, auto
from environs import Env
from time import sleep
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler

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


def phone_request(update, context):
    keyboard = [
        [KeyboardButton('Отправить номер телефона', request_contact=True)],
        ['Гостевая ссылка (без входа)'],
        ['Отмена'],
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
    logger.debug(f'PAYLOAD - {payload}')
    response = requests.post(api_url, data=payload)
    logger.debug(f'API_URL - {response.url}')
    logger.debug(f'RESPONSE_STATUS - {response}')
    # logger.debug(f'RESPONSE - {response.json()}')
    response.raise_for_status()

    # for user_reg_status, user_link in response.json().items():
    #     if user_reg_status == 'register':
    #         text = f'Зарегистрируйтесь по ссылке:\n{user_link}'
    #     elif user_reg_status == 'login':
    #         text = f'Войдите по ссылке:\n{user_link}'
    text = response.text
    update.message.reply_text(text, reply_markup=ReplyKeyboardRemove())
    return States.REQUEST


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
            States.REQUEST: [
                MessageHandler(Filters.contact, get_api_respone),
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