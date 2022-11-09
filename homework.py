import json
import logging
import os
import sys
import time
import requests

from сustomexcept import CheckResponsDictError, TelegramMessageError
from dotenv import load_dotenv
from telegram import Bot


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('log.log'),
              logging.StreamHandler(sys.stdout)])

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TEL_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """ функция отправки сообщения в телеграм чат """
    bot = Bot(token=TELEGRAM_TOKEN)
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'сообщение отправлено в телеграм,{message}')
    except Exception:
        raise TelegramMessegeError('сообщение не отправлено')


def get_api_answer(current_timestamp):
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != 200:
        return_code = response.status_code
        logger.error(f'YaAPI недоступен ошибка: {return_code}')
        raise Exception
    response = response.json()
    return response


def check_response(response):
    try:
        if response.__class__.__name__ != 'dict':
            raise Exception('с сервера вернулся не список')
    except Exception :
        logger.error('вернулся отличный от словаря ответ')
    try:
        if response == {}:
            raise CheckResponsDictError('вернулся пустой словарь')
    except Exception:
        logger.error('пусто')
    try:
        homework = response['homeworks']
        if homework.__class__.__name__ != 'list':
            raise Exception('в словаре под ключом "homeworks" не список')
    except KeyError:
        logger.error('отсутвует ключ "homeworks"')
    return homework


def parse_status(homework):
    try:
        homework_name = homework['homework_name']
    except KeyError:
        logger.error('нет ключа "homework_name" ')

    homework_status = homework['status']
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('не все токены введены корректно')
    logger.debug('Старт бота')
    current_timestamp = 0#int(time.time())
    bot = Bot(token=TELEGRAM_TOKEN)
    while True:
        try:
            all_homework = get_api_answer(current_timestamp)
            check_homework = check_response(all_homework)

            if len(check_homework) > 0:
                homework = check_homework[0]
                send_message(bot, parse_status(homework))
                current_timestamp = all_homework['current_date']
            time.sleep(RETRY_TIME)
        except Exception as e:
            logger.error(f'Бот упал с ошибкой {e}')
            send_message(bot, f'Бот упал с ошибкой: {e}')
            time.sleep(60)


if __name__ == '__main__':
    main()
