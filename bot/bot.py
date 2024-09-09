import logging
import re
import subprocess
import psycopg2
import os
import paramiko
from io import BytesIO
from datetime import datetime, timedelta
from telebot import types
import telebot

# Настройка логгера
logging.basicConfig(filename='bot.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(filename)s - %(lineno)d - %(message)s')
logger = logging.getLogger(__name__)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)  # Устанавливаем уровень логирования для консоли
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))  # Форматируем вывод в консоль
logger.addHandler(console_handler)


# Переменные окружения
TOKEN = os.environ['TOKEN']
RM_HOST = os.environ['RM_HOST']
RM_PORT = int(os.environ['RM_PORT'])
RM_USER = os.environ['RM_USER']
RM_PASSWORD = os.environ['RM_PASSWORD']
DB_USER = os.environ['DB_USER']
DB_PASSWORD = os.environ['DB_PASSWORD']
DB_HOST = os.environ['DB_HOST']
DB_PORT = int(os.environ['DB_PORT'])
DB_DATABASE = os.environ['DB_DATABASE']
DB_REPL_USER = os.environ['DB_REPL_USER']
DB_REPL_PASSWORD = os.environ['DB_REPL_PASSWORD']
DB_REPL_HOST = os.environ['DB_REPL_HOST']
DB_REPL_PORT = int(os.environ['DB_REPL_PORT'])

# Подключение к Telegram API
bot = telebot.TeleBot(TOKEN)

def connect_to_remote_server():
    """Подключается к удаленному серверу через SSH."""
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh_client.connect(
            hostname=RM_HOST,
            port=RM_PORT,
            username=RM_USER,
            password=RM_PASSWORD
        )
        return ssh_client
    except Exception as e:
        logging.error(f"Ошибка подключения к SSH: {e}")
        return None


def execute_command(ssh_client, command):
    """Выполняет команду на удаленном сервере через SSH."""
    if ssh_client:
        stdin, stdout, stderr = ssh_client.exec_command(command)
        output = stdout.read().decode()
        error = stderr.read().decode()
        if error:
            logging.error(f"Ошибка выполнения команды: {error}")
            return None
        else:
            return output
    else:
        logging.error("Ошибка подключения к SSH.")
        return None


def execute_sql(query):
    """Выполняет SQL-запрос через SSH и psql."""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(RM_HOST, username=RM_USER, password=RM_PASSWORD)

        # Выполняем команду psql
        stdin, stdout, stderr = ssh.exec_command(
            f"psql -h {DB_HOST} -d {DB_DATABASE} -U {DB_USER} -c \"{query}\""
        )
        output = stdout.read().decode('utf-8').strip()

        ssh.close()
        return output

    except Exception as e:
        logger.error(f"Ошибка при выполнении SQL-запроса: {e}")
        return f"Ошибка при выполнении SQL-запроса: {e}"


# Регулярные выражения
email_regex = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
phone_regex = r'\+?\d{1,3}[-\s.]?\d{1,3}[-\s.]?\d{3,4}[-\s.]?\d{3,4}'
password_regex = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()])[A-Za-z\d!@#$%^&*()]{8,}$"

# Словарь для хранения найденных данных
found_data = {}


def find_email(message: telebot.types.Message):
    """Обрабатывает команду /find_email."""
    logger.info(f"Получена команда /find_email от пользователя: {message.from_user.username}")
    bot.send_message(message.chat.id, "Введите текст, в котором нужно найти email-адреса:")
    bot.register_next_step_handler(message, process_email)


def process_email(message: telebot.types.Message):
    """Обрабатывает ввод текста для поиска email."""
    text = message.text
    emails = re.findall(email_regex, text)
    if emails:
        bot.send_message(message.chat.id, f"Найденные email-адреса:\n{', '.join(emails)}")
        found_data[message.chat.id] = emails  # Сохраняем найденные данные
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Записать в базу данных", callback_data="save_emails"))
        bot.send_message(message.chat.id, "Хотите записать email в базу данных?", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "В тексте не найдены email-адреса.")


def get_emails(message: telebot.types.Message):
    """Обрабатывает команду /get_emails."""
    logger.info(f"Получена команда /get_emails от пользователя: {message.from_user.username}")
    query = "SELECT email FROM user_emails"
    result = execute_sql(query)
    if result:
        bot.send_message(message.chat.id, f"Найденные email-адреса:\n{result}")
    else:
        bot.send_message(message.chat.id, "Email-адреса не найдены.")


def find_phone_number(message: telebot.types.Message):
    """Обрабатывает команду /find_phone_number."""
    logger.info(f"Получена команда /find_phone_number от пользователя: {message.from_user.username}")
    bot.send_message(message.chat.id, "Введите текст, в котором нужно найти номера телефонов:")
    bot.register_next_step_handler(message, process_phone_number)


def process_phone_number(message: telebot.types.Message):
    """Обрабатывает ввод текста для поиска номеров телефонов."""
    text = message.text
    phone_numbers = re.findall(phone_regex, text)
    if phone_numbers:
        bot.send_message(message.chat.id, f"Найденные номера телефонов:\n{', '.join(phone_numbers)}")
        found_data[message.chat.id] = phone_numbers  # Сохраняем найденные данные
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Записать в базу данных", callback_data="save_phone_numbers"))
        bot.send_message(message.chat.id, "Хотите записать номера телефонов в базу данных?", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "В тексте не найдены номера телефонов.")


def save_emails(message: telebot.types.Message):
    """Обрабатывает запрос на сохранение email в базу данных."""
    logger.info(f"Получен запрос на сохранение email-адресов от пользователя: {message.from_user.username}")
    emails = found_data.get(message.chat.id)
    if emails:
        for email in emails:
            query = f"INSERT INTO user_emails (email) VALUES ('{email}');"
            result = execute_sql(query)
            if result:
                bot.send_message(message.chat.id, f"Email-адрес '{email}' успешно записан в базу данных!")
            else:
                bot.send_message(message.chat.id, f"Произошла ошибка при записи email-адреса '{email}' в базу данных.")
        del found_data[message.chat.id]  # Удаляем данные из хранилища
    else:
        bot.send_message(message.chat.id, "Произошла ошибка. Попробуйте еще раз.")


def save_phone_numbers(message: telebot.types.Message):
    """Обрабатывает запрос на сохранение номеров телефонов в базу данных."""
    logger.info(f"Получен запрос на сохранение номеров телефонов от пользователя: {message.from_user.username}")
    phone_numbers = found_data.get(message.chat.id)
    if phone_numbers:
        for phone_number in phone_numbers:
            query = f"INSERT INTO user_phones (phone) VALUES ('{phone}');"
            result = execute_sql(query)
            if result:
                bot.send_message(message.chat.id, f"Номер телефона '{phone_number}' успешно записан в базу данных!")
            else:
                bot.send_message(message.chat.id, f"Произошла ошибка при записи номера телефона '{phone_number}' в базу данных.")
        del found_data[message.chat.id]  # Удаляем данные из хранилища
    else:
        bot.send_message(message.chat.id, "Произошла ошибка. Попробуйте еще раз.")


def get_phone_numbers(message: telebot.types.Message):
    """Обрабатывает команду /get_phone_numbers."""
    logger.info(f"Получена команда /get_phone_numbers от пользователя: {message.from_user.username}")
    query = "SELECT phone FROM user_phones;"
    result = execute_sql(query)
    if result:
        bot.send_message(message.chat.id, f"Найденные номера телефонов:\n{result}")
    else:
        bot.send_message(message.chat.id, "Номера телефонов не найдены.")


def get_data(message: telebot.types.Message):
    """Обрабатывает команду /get_data."""
    logger.info(f"Получена команда /get_data от пользователя: {message.from_user.username}")
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Получить email", callback_data="get_emails"),
               types.InlineKeyboardButton("Получить номера телефонов", callback_data="get_phone_numbers"))
    bot.send_message(message.chat.id, "Выберите тип данных:", reply_markup=markup)


def verify_password(message: telebot.types.Message):
    """Обрабатывает команду /verify_password."""
    logger.info(f"Получена команда /verify_password от пользователя: {message.from_user.username}")
    bot.send_message(message.chat.id, "Введите пароль для проверки:")
    bot.register_next_step_handler(message, process_password)


def process_password(message: telebot.types.Message):
    """Обрабатывает ввод пароля для проверки."""
    password = message.text
    if re.match(password_regex, password):
        bot.send_message(message.chat.id, "Пароль сложный")
    else:
        bot.send_message(message.chat.id, "Пароль простой")


def get_release(message: telebot.types.Message):
    """Обрабатывает команду /get_release."""
    logger.info(f"Получена команда /get_release от пользователя: {message.from_user.username}")
    ssh_client = connect_to_remote_server()
    if ssh_client:
        output = execute_command(ssh_client, "lsb_release -a")
        if output:
            bot.send_message(message.chat.id, f"Информация о релизе:\n{output}")
        ssh_client.close()
    else:
        bot.send_message(message.chat.id, "Ошибка подключения к серверу.")


def get_uname(message: telebot.types.Message):
    """Обрабатывает команду /get_uname."""
    logger.info(f"Получена команда /get_uname от пользователя: {message.from_user.username}")
    ssh_client = connect_to_remote_server()
    if ssh_client:
        output = execute_command(ssh_client, "uname -a")
        if output:
            bot.send_message(message.chat.id, f"Информация о системе:\n{output}")
        ssh_client.close()
    else:
        bot.send_message(message.chat.id, "Ошибка подключения к серверу.")


def get_uptime(message: telebot.types.Message):
    """Обрабатывает команду /get_uptime."""
    logger.info(f"Получена команда /get_uptime от пользователя: {message.from_user.username}")
    ssh_client = connect_to_remote_server()
    if ssh_client:
        output = execute_command(ssh_client, "uptime")
        if output:
            bot.send_message(message.chat.id, f"Время работы системы:\n{output}")
        ssh_client.close()
    else:
        bot.send_message(message.chat.id, "Ошибка подключения к серверу.")


def get_df(message: telebot.types.Message):
    """Обрабатывает команду /get_df."""
    logger.info(f"Получена команда /get_df от пользователя: {message.from_user.username}")
    ssh_client = connect_to_remote_server()
    if ssh_client:
        output = execute_command(ssh_client, "df -h")
        if output:
            if len(output) > 4096:
                for i in range(0, len(output), 4096):
                    bot.send_message(message.chat.id, output[i:i+4096])
            else:
                bot.send_message(message.chat.id, output)
        ssh_client.close()
    else:
        bot.send_message(message.chat.id, "Ошибка подключения к серверу.")


def get_free(message: telebot.types.Message):
    """Обрабатывает команду /get_free."""
    logger.info(f"Получена команда /get_free от пользователя: {message.from_user.username}")
    ssh_client = connect_to_remote_server()
    if ssh_client:
        output = execute_command(ssh_client, "free -h")
        if output:
            bot.send_message(message.chat.id, output)
        ssh_client.close()
    else:
        bot.send_message(message.chat.id, "Ошибка подключения к серверу.")


def get_mpstat(message: telebot.types.Message):
    """Обрабатывает команду /get_mpstat."""
    logger.info(f"Получена команда /get_mpstat от пользователя: {message.from_user.username}")
    ssh_client = connect_to_remote_server()
    if ssh_client:
        output = execute_command(ssh_client, "mpstat -P ALL 10 1")
        if output:
            # Создаем файл в памяти
            file_like_object = BytesIO(output.encode('utf-8'))
            file_like_object.name = "mpstat_output.txt"

            # Отправляем файл пользователю
            bot.send_document(message.chat.id, file_like_object)
        ssh_client.close()
    else:
        bot.send_message(message.chat.id, "Ошибка подключения к серверу.")


def get_w(message: telebot.types.Message):
    """Обрабатывает команду /get_w."""
    logger.info(f"Получена команда /get_w от пользователя: {message.from_user.username}")
    ssh_client = connect_to_remote_server()
    if ssh_client:
        output = execute_command(ssh_client, "w")
        if output:
            bot.send_message(message.chat.id, output)
        ssh_client.close()
    else:
        bot.send_message(message.chat.id, "Ошибка подключения к серверу.")


def get_auths(message: telebot.types.Message):
    """Обрабатывает команду /get_auths."""
    logger.info(f"Получена команда /get_auths от пользователя: {message.from_user.username}")
    ssh_client = connect_to_remote_server()
    if ssh_client:
        output = execute_command(ssh_client, "last -n 10")
        if output:
            # Создаем файл в памяти
            file_like_object = BytesIO(output.encode('utf-8'))
            file_like_object.name = "last_output.txt"

            # Отправляем файл пользователю
            bot.send_document(message.chat.id, file_like_object)
        ssh_client.close()
    else:
        bot.send_message(message.chat.id, "Ошибка подключения к серверу.")


def get_critical(message: telebot.types.Message):
    """Обрабатывает команду /get_critical."""
    logger.info(f"Получена команда /get_critical от пользователя: {message.from_user.username}")
    ssh_client = connect_to_remote_server()
    if ssh_client:
        output = execute_command(ssh_client, "sudo journalctl -p 2 -n 5")
        if output:
            # Создаем файл в памяти
            file_like_object = BytesIO(output.encode('utf-8'))
            file_like_object.name = "critical_events.txt"

            # Отправляем файл пользователю
            bot.send_document(message.chat.id, file_like_object)
        else:
            bot.send_message(message.chat.id, "Критических событий за последние 5 записей не найдено.")
        ssh_client.close()
    else:
        bot.send_message(message.chat.id, "Ошибка подключения к серверу.")


def get_ps(message: telebot.types.Message):
    """Обрабатывает команду /get_ps."""
    logger.info(f"Получена команда /get_ps от пользователя: {message.from_user.username}")
    ssh_client = connect_to_remote_server()
    if ssh_client:
        output = execute_command(ssh_client, "sudo ps aux")
        if output:
            # Создаем файл в памяти
            file_like_object = BytesIO(output.encode('utf-8'))
            file_like_object.name = "ps_output.txt"

            # Отправляем файл пользователю
            bot.send_document(message.chat.id, file_like_object)
        ssh_client.close()
    else:
        bot.send_message(message.chat.id, "Ошибка подключения к серверу.")


def get_ss(message: telebot.types.Message):
    """Обрабатывает команду /get_ss."""
    logger.info(f"Получена команда /get_ss от пользователя: {message.from_user.username}")
    ssh_client = connect_to_remote_server()
    if ssh_client:
        output = execute_command(ssh_client, "sudo ss -a")
        if output:
            # Создаем файл в памяти
            file_like_object = BytesIO(output.encode('utf-8'))
            file_like_object.name = "ss_output.txt"

            # Отправляем файл пользователю
            bot.send_document(message.chat.id, file_like_object)
        ssh_client.close()
    else:
        bot.send_message(message.chat.id, "Ошибка подключения к серверу.")


def get_apt_list(message: telebot.types.Message):
    """Обрабатывает команду /get_apt_list."""
    logger.info(f"Получена команда /get_apt_list от пользователя: {message.from_user.username}")
    bot.send_message(message.chat.id, "Введите 'all' для получения списка всех пакетов, или название пакета:")
    bot.register_next_step_handler(message, process_apt_list)


def process_apt_list(message: telebot.types.Message):
    """Обрабатывает ввод названия пакета для /get_apt_list."""
    logger.debug(f"Полученное название пакета: {message.text}")
    package_name = message.text
    ssh_client = connect_to_remote_server()
    if ssh_client:
        if package_name.lower() == "all":
            output = execute_command(ssh_client, "apt list --installed")
            if output:
                # Создаем файл в памяти
                file_like_object = BytesIO(output.encode('utf-8'))
                file_like_object.name = "apt_list_output.txt"

                # Отправляем файл пользователю
                bot.send_document(message.chat.id, file_like_object)
        else:
            output = execute_command(ssh_client, f"apt-cache policy {package_name}")
            if output:
                # Создаем файл в памяти
                file_like_object = BytesIO(output.encode('utf-8'))
                file_like_object.name = "apt_list_output.txt"

                # Отправляем файл пользователю
                bot.send_document(message.chat.id, file_like_object)
        ssh_client.close()
    else:
        bot.send_message(message.chat.id, "Ошибка подключения к серверу.")


def get_services(message: telebot.types.Message):
    """Обрабатывает команду /get_services."""
    logger.info(f"Получена команда /get_services от пользователя: {message.from_user.username}")
    ssh_client = connect_to_remote_server()
    if ssh_client:
        output = execute_command(ssh_client, "systemctl list-units --type=service --all")
        if output:
            # Создаем файл в памяти
            file_like_object = BytesIO(output.encode('utf-8'))
            file_like_object.name = "services_list.txt"

            # Отправляем файл пользователю
            bot.send_document(message.chat.id, file_like_object)
        else:
            bot.send_message(message.chat.id, "Информация о сервисах не найдена.")
        ssh_client.close()
    else:
        bot.send_message(message.chat.id, "Ошибка подключения к серверу.")


def get_repl_logs(message: telebot.types.Message):
    """Обрабатывает команду /get_repl_logs."""
    logger.info(f"Получена команда /get_repl_logs от пользователя: {message.from_user.username}")
    ssh_client = connect_to_remote_server()
    if ssh_client:
        output = execute_command(ssh_client, "sudo tail /data/postgresql_master_log/postgresql.log")
        if output:
            # Создаем файл в памяти
            file_like_object = BytesIO(output.encode('utf-8'))
            file_like_object.name = "repl_logs.txt"

            # Отправляем файл пользователю
            bot.send_document(message.chat.id, file_like_object)
        else:
            bot.send_message(message.chat.id, "Логи репликации не найдены.")
        ssh_client.close()
    else:
        bot.send_message(message.chat.id, "Ошибка подключения к серверу.")


# --- Обработка команды /start ---
@bot.message_handler(commands=['start'])
def send_welcome(message: telebot.types.Message):
    """Отправляет приветственное сообщение."""
    logger.info(f"Получена команда /start от пользователя: {message.from_user.username}")
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Поиск email", "Поиск телефона", "Проверка пароля", "Мониторинг системы",
               "Получить email", "Получить номера телефонов")
    bot.send_message(message.chat.id, "Привет! Я ваш телеграмм-бот. 👋\n\n"
                          "Что вы хотите сделать?", reply_markup=markup)


# --- Обработка кнопок ---
@bot.message_handler(func=lambda message: message.text in ["Поиск email", "Поиск телефона", "Проверка пароля",
                                                           "Мониторинг системы", "Получить email", "Получить номера телефонов"])
def handle_button(message: telebot.types.Message):
    """Обрабатывает нажатие на кнопки."""
    if message.text == "Поиск email":
        find_email(message)
    elif message.text == "Поиск телефона":
        find_phone_number(message)
    elif message.text == "Проверка пароля":
        verify_password(message)
    elif message.text == "Получить email":
        get_emails(message)
    elif message.text == "Получить номера телефонов":
        get_phone_numbers(message)
    elif message.text == "Мониторинг системы":
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("get_release", "get_uname", "get_uptime", "get_df", "get_free", "get_mpstat", "get_w",
                  "get_auths", "get_critical", "get_ps", "get_ss", "get_apt_list", "get_services", "get_repl_logs")
        bot.send_message(message.chat.id, "Выберите команду мониторинга:", reply_markup=markup)


# --- Обработка команд мониторинга ---
@bot.message_handler(func=lambda message: message.text in ["get_release", "get_uname", "get_uptime", "get_df", "get_free", "get_mpstat", "get_w",
                  "get_auths", "get_critical", "get_ps", "get_ss", "get_apt_list", "get_services", "get_repl_logs"])
def handle_monitoring_command(message: telebot.types.Message):
    """Обрабатывает команды мониторинга."""
    logger.debug(f"Получена команда мониторинга: {message.text}")

    if message.text == "get_release":
        get_release(message)
    elif message.text == "get_uname":
        get_uname(message)
    elif message.text == "get_uptime":
        get_uptime(message)
    elif message.text == "get_df":
        get_df(message)
    elif message.text == "get_free":
        get_free(message)
    elif message.text == "get_mpstat":
        get_mpstat(message)
    elif message.text == "get_w":
        get_w(message)
    elif message.text == "get_auths":
        get_auths(message)
    elif message.text == "get_critical":
        get_critical(message)
    elif message.text == "get_ps":
        get_ps(message)
    elif message.text == "get_ss":
        get_ss(message)
    elif message.text == "get_apt_list":
        get_apt_list(message)
    elif message.text == "get_services":
        get_services(message)
    elif message.text == "get_repl_logs":
        get_repl_logs(message)


# --- Обработка нажатия на кнопки ---
@bot.callback_query_handler(func=lambda call: call.data in ["save_emails", "save_phone_numbers"])
def handle_callback_query(call: types.CallbackQuery):
    """Обрабатывает нажатие на кнопки "Сохранить"."""
    if call.data == "save_emails":
        save_emails(call.message)
    elif call.data == "save_phone_numbers":
        save_phone_numbers(call.message)


# --- Запуск бота ---
if __name__ == '__main__':
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        logger.error(f"Ошибка при работе бота: {e}")
