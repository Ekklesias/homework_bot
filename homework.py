import logging
import os
import requests
import sys
import time
from dotenv import load_dotenv
from http import HTTPStatus

import telegram

import exceptions

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO)

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())


RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all([TELEGRAM_TOKEN, PRACTICUM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        logging.debug('Попытка отправки сообщения в telegram')
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Отправка сообщения в telegram')
    except telegram.error.TelegramError as error:
        logging.error(f'Не удалось отправить сообщение: {error}')
        raise Exception(error)


def get_api_answer(timestamp):
    """Получить данные о статусе работы."""
    timestamp = timestamp or int(time.time())
    params_request = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp},
    }
    try:
        logging.info('Начало запроса к API')
        response = requests.get(**params_request)
        if response.status_code != HTTPStatus.OK:
            raise exceptions.InvalidResponseCode(
                'Не удалось получить ответ API, '
                f'ошибка: {response.status_code}'
                f'причина: {response.reason}'
                f'текст: {response.text}')
        return response.json()
    except Exception:
        raise exceptions.ConnectinError(
            'Не верный код ответа параметры запроса: url = {url},'
            'headers = {headers},'
            'params = {params}'.format(**params_request))


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError('response не типа dict')
    if 'homeworks' not in response:
        raise exceptions.EmptyResponseError('От API пришёл пустой ответ.')
    if 'current_date' not in response:
        raise exceptions.EmptyResponseError('От API пришёл пустой ответ.')
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError('Homeworks не типа list')
    return homeworks


def parse_status(homework):
    """Извлекает из инфы о конкретной домашней работе статус этой работы."""
    if 'homework_name' not in homework:
        raise KeyError('В ответе отсутсвует ключ homework_name')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Некорректный статус работы - {homework_status}')
    return (
        f'Изменился статус проверки работы "{homework_name}"'
        f'{HOMEWORK_VERDICTS[homework_status]}'
    )


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутсвуют необходимые переменные окружения')
        sys.exit('Нет переменных окружения')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    current_report = {}
    prev_report = {}
    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_timestamp = (
                response.get('current_date', current_timestamp)
            )
            homeworks = check_response(response)
            if homeworks:
                homework = homeworks[0]
                current_report['name'] = homework.get('homework_name')
                status = parse_status(homework)
                current_report['messages'] = status
            else:
                current_report['messages'] = 'Статус не изменился'
                status = 'Статус не изменился'
            if current_report != prev_report:
                send_message(bot=bot, message=status)
                prev_report = current_report.copy()
            else:
                logger.debug('Нет новых статусов работы')
        except Exception as error:
            error_text = f'Ошибка {error}.'
            logger.error(error, exc_info=True)
            current_report['messages'] = error_text
            if current_report != prev_report:
                send_message(bot=bot, message=error_text)
                prev_report = current_report.copy()
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
