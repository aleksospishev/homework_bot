import json
import logging
import os
import sys
import time
import requests

from сustomexcept import TelegramMessageError
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
    """Функция отправки сообщения в телеграм чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'сообщение отправлено в телеграм,{message}')
    except TelegramMessageError:
        logger.error('сообщение не отправлено')


def get_api_answer(current_timestamp):
    """Ответ в формате JSON от API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != 200:
        return_code = response.status_code
        logger.error(f'YaAPI недоступен ошибка: {return_code}')
        raise Exception
    try:
        response = response.json()
        return response
    except json.JSONDecodeError:
        logging.error('некорректный JSON')


def check_response(response):
    """Проверка получаемого ответа от API."""
    if not isinstance(response, dict):
        raise TypeError('Вернулся отличный от словаря ответ')
    if not response.get('homeworks'):
        KeyError('Отсутвует ключ "homeworks"')
    homework = response['homeworks']
    if not isinstance(homework, list):
        raise TypeError('В словаре под ключом "homeworks" не список')
    return homework


def parse_status(homework):
    """Возвращаем статус проверяемой работы."""
    try:
        name_homework = homework['homework_name']
    except KeyError as e:
        logger.error(f'в словаре нет ключа {e}')
    if homework['status'] not in HOMEWORK_STATUSES:
        raise KeyError(f'у работы неверный статус {homework["status"]}')
    homework_status = homework['status']
    verdict = HOMEWORK_STATUSES[homework_status]

    return f'Изменился статус проверки работы "{name_homework}". {verdict}'


def check_tokens():
    """проверка переменных из окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('не все токены введены корректно')
    logger.debug('Старт бота')
    current_timestamp = int(time.time())
    bot = Bot(token=TELEGRAM_TOKEN)
    while True:
        try:
            all_homework = get_api_answer(current_timestamp)
            check_homework = check_response(all_homework)
            if len(check_homework) > 0:
                homework = check_homework[0]
                send_message(bot, parse_status(homework))
                current_timestamp = all_homework['current_date']
        except Exception as e:
            logger.error(f'Бот упал с ошибкой {e}')
            send_message(bot, f'Бот упал с ошибкой: {e}')
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
