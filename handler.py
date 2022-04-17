import datetime
from loader import bot
# import re
# from telebot import TeleBot
from telebot.types import Message
# from telebot.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, \
#     KeyboardButton
# from rapidapi import city_founding, lowprice_highprice_command, bestdeal_command
# from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP
# from datetime import date
from loguru import logger
# from user_db import *
# from history_db import *

logger.add('log.log', format="{time} {level} {message}", level='INFO')


@logger.catch
@bot.message_handler(commands=['start'])
def start_message(message: Message) -> None:
    """
    Функция, которая выполняет команду /start
    """
    logger.info("User {user} used a command /start".format(user=message.chat.id))
    bot.send_message(chat_id=message.chat.id, text=f'Добрый день, {message.from_user.first_name}!')
    help_handler(message)


@logger.catch
@bot.message_handler(commands=['help'])
def help_handler(message: Message) -> None:
    """
    Функция, которая выполняет команду /help
    """
    logger.info("User {user} used a command /help".format(user=message.chat.id))
    bot.send_message(chat_id=message.chat.id,
                     text='Вы можете управлять мной с помощью следующих команд:\n'
                          '/lowprice - узнать топ самых дешёвых отелей в городе\n'
                          '/highprice - узнать топ самых дорогих отелей в городе\n'
                          '/bestdeal - узнать топ отелей, наиболее подходящих по цене и расположению от центра'
                          '/history - узнать историю поиска отелей')


@logger.catch
@bot.message_handler(commands=['lowprice', 'highprice', 'bestdeal'])
def start(message: Message) -> None:
    """
    Функция, которая выполняет команду /lowprice, /highprice или /bestdeal
    """
    logger.info("User {user} used a command {command}".format(user=message.chat.id, command=message.text))
    cur_user = User.get_user(user_id=message.chat.id)
    cur_user.command = message.text
    bot.send_message(chat_id=message.chat.id, text='В какой город вы хотите поехать?')
    bot.register_next_step_handler(message=message, callback=city_markup)


def city_markup(message: Message):
    """
    Функция для создания кнопок районоов города
    """
    city = message.text
    cities = city_founding(city)
    if len(cities) == 0:
        bot.send_message(chat_id=message.chat.id,
                         text='Город не найден. Попробуйте ввести ещё раз')
        bot.register_next_step_handler(message=message, callback=city_markup)
    inline_keyboard = InlineKeyboardMarkup(row_width=3)
    for city_id, index_city in cities.items():
        inline_button = InlineKeyboardButton(text=index_city, callback_data=city_id)
        inline_keyboard.add(inline_button)
    inline_button = InlineKeyboardButton(text='Выбрать другой город: ', callback_data='777')
    inline_keyboard.add(inline_button)
    bot.send_message(chat_id=message.from_user.id, text='Уточните, пожалуйста: ', reply_markup=inline_keyboard)


@bot.callback_query_handler(func=lambda call: re.fullmatch(r'\d{3,}', call.data))
def city_callback_query(cal: CallbackQuery) -> None:
    """
    Функция для обработки id указанного города
    """
    if cal.data == '777':
        bot.send_message(chat_id=cal.message.chat.id, text='В какой город вы хотите поехать?')
        bot.register_next_step_handler(message=cal.message, callback=city_markup)
        return
    cur_user = User.get_user(user_id=cal.message.chat.id)
    cur_user.city_id = cal.data
    command = cur_user.command
    bot.edit_message_text(chat_id=cal.message.chat.id, message_id=cal.message.message_id, text=f'Город выбран')
    if command == '/lowprice' or command == '/highprice':
        new_message = bot.send_message(chat_id=cal.message.chat.id, text='Выберите дату заезда')
        create_check_in(message=new_message)
    else:
        new_message = bot.send_message(chat_id=cal.message.chat.id,
                                       text='Укажите диапозон цен через пробел(минимум и максимум)\n'
                                            'например 500 1000')  # 500 1000
        bot.register_next_step_handler(message=new_message, callback=get_price_range)


@logger.catch
def get_price_range(message: Message) -> None:
    """
    Функция принимает диапозон цен(минимальное и максимальное значение) для команды /bestdeal
    """
    if re.fullmatch(r'\d+\s\d+', message.text):
        price = message.text.split()
        minimal_price = price[0]
        maximal_price = price[1]
        if int(minimal_price) > int(maximal_price):
            maximal_price, minimal_price = minimal_price, minimal_price
        cur_user = User.get_user(user_id=message.chat.id)
        cur_user.price_min = minimal_price
        cur_user.price_max = maximal_price
        new_message = bot.send_message(chat_id=message.chat.id,
                                       text='Введите диапозон расстояния(через пробел), на котором находится отель от центра\n'
                                            'например: 2 10\n'
                                            'или максимально допустимое расстояние до центра\n'
                                            'например: 10\n')
        bot.register_next_step_handler(message=new_message, callback=get_distance_range)
    else:
        bot.send_message(chat_id=message.chat.id,
                         text='Неверно введены данные\nУкажите диапозон цен через пробел(минимум и максимум)\n'
                              'например 500 1000')
        bot.register_next_step_handler(message=message, callback=get_price_range)


@logger.catch
def get_distance_range(message: Message) -> None:
    """
    Функция принимает диапозон расстояния, на котором находиться отель от центра для команды /bestdeal
    """
    if re.fullmatch(r'\d+\s\d+', message.text):
        distance = message.text.split()
        minimal_distance = distance[0]
        maximal_distance = distance[1]
        if int(minimal_distance) > int(maximal_distance):
            maximal_distance, minimal_distance = minimal_distance, maximal_distance
        cur_user = User.get_user(user_id=message.chat.id)
        cur_user.distance_min = minimal_distance
        cur_user.distance_max = maximal_distance
        bot.send_message(chat_id=message.chat.id, text='Выберите дату заезда')
        create_check_in(message)
    elif re.fullmatch(r'[1-9]\d+', message.text):
        cur_user = User.get_user(user_id=message.chat.id)
        cur_user.distance_min = 0
        cur_user.distance_max = message.text
        bot.send_message(chat_id=message.chat.id, text='Выберите дату заезда')
        create_check_in(message)
    else:
        new_message = bot.send_message(chat_id=message.chat.id,
                                       text='Неверно введены данные\nВведите диапозон расстояния(через пробел), на котором находится отель от центра\n'
                                            'например: 2 10')
        bot.register_next_step_handler(message=new_message, callback=get_distance_range)


@logger.catch
def create_check_in(message: Message) -> None:
    """
    Функция создаёт кадендарь для даты заезда
    """
    calendar, step = DetailedTelegramCalendar(calendar_id='in',
                                              locale='ru',
                                              min_date=date.today(),
                                              max_date=date(2024, 3, 31)).build()
    bot.send_message(chat_id=message.chat.id,
                     text=f'Select {LSTEP[step]}',
                     reply_markup=calendar)
    # bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)


@logger.catch
@bot.callback_query_handler(func=DetailedTelegramCalendar.func(calendar_id='in'))
def callback_check_in(cal: CallbackQuery) -> None:
    """
    Функция обрабатывает дату заезда по календарю
    """
    result, key, step = DetailedTelegramCalendar(calendar_id='in',
                                                 locale='ru',
                                                 min_date=date.today(),
                                                 max_date=date(2024, 3, 31)).process(call_data=cal.data)
    if not result and key:
        bot.edit_message_text(f'Select {LSTEP[step]}',
                              chat_id=cal.message.chat.id,
                              message_id=cal.message.message_id,
                              reply_markup=key)
    elif result:
        bot.edit_message_text(f"Дата заезда: {result}",
                              chat_id=cal.message.chat.id,
                              message_id=cal.message.message_id)
        cur_user = User.get_user(user_id=cal.message.chat.id)
        cur_user.check_in = result
        new_message = bot.send_message(chat_id=cal.message.chat.id, text='Выберите дату выезда')
        create_check_out(message=new_message)


def create_check_out(message: Message) -> None:
    """
    Функция создаёт кадендарь для даты выезда
    """
    cur_user = User.get_user(user_id=message.chat.id)
    check_in_date = cur_user.check_in
    current_date = datetime.datetime.strptime(str(check_in_date), '%Y-%m-%d').date()
    calendar, step = DetailedTelegramCalendar(calendar_id='out',
                                              locale='ru',
                                              min_date=date(current_date.year, current_date.month, current_date.day),
                                              max_date=date(2024, 3, 31)).build()
    bot.send_message(chat_id=message.chat.id,
                     text=f'Select {LSTEP[step]}',
                     reply_markup=calendar)


@bot.callback_query_handler(func=DetailedTelegramCalendar.func(calendar_id='out'))
def callback_check_out(cal: CallbackQuery):
    """
    Функция обрабатывает дату выезда по календарю
    """
    cur_user = User.get_user(user_id=cal.message.chat.id)
    check_in_date = cur_user.check_in
    current_date = datetime.datetime.strptime(str(check_in_date), '%Y-%m-%d').date()
    result, key, step = DetailedTelegramCalendar(calendar_id='out',
                                                 locale='ru',
                                                 min_date=date(current_date.year, current_date.month, current_date.day),
                                                 max_date=date(2024, 3, 31)).process(call_data=cal.data)
    if not result and key:
        bot.edit_message_text(f'Select {LSTEP[step]}',
                              chat_id=cal.message.chat.id,
                              message_id=cal.message.message_id,
                              reply_markup=key)
    elif result:
        bot.edit_message_text(f"Дата выезда: {result}",
                              chat_id=cal.message.chat.id,
                              message_id=cal.message.message_id)
        cur_user.check_out = result
        keyboard = ReplyKeyboardMarkup(row_width=10)
        buttons = []
        for index_button in range(1, 21):
            button = KeyboardButton(str(index_button))
            buttons.append(button)
        keyboard.add(*buttons)
        new_message = bot.send_message(chat_id=cal.message.chat.id,
                                       text='Укажите сколько вы хотите вывести отелей',
                                       reply_markup=keyboard)
        bot.register_next_step_handler(message=new_message, callback=hotels_count)


@logger.catch
def hotels_count(message: Message) -> None:
    """
    Функция принимает на вход количетсво отелей и проверяет на корректность
    """
    if not message.text.isdigit():
        bot.send_message(chat_id=message.chat.id,
                         text='Некорректный ввод! Введите цифры')
        bot.register_next_step_handler(message=message, callback=hotels_count)
        return
    if int(message.text) < 0 or int(message.text) > 25:
        bot.send_message(chat_id=message.chat.id,
                         text='Неверный ввод! Введите цифру от 1 до 25')
        bot.register_next_step_handler(message=message, callback=hotels_count)
    cur_user = User.get_user(user_id=message.chat.id)
    cur_user.hotel_count = message.text
    keyboard = ReplyKeyboardMarkup()
    button_1 = KeyboardButton(text='да')
    button_2 = KeyboardButton(text='нет')
    keyboard.add(button_1, button_2)
    new_message = bot.send_message(chat_id=message.chat.id,
                                   text='Вывести фотографии?',
                                   reply_markup=keyboard)
    bot.register_next_step_handler(message=new_message, callback=check_hotel_photo)


@logger.catch
def check_hotel_photo(message: Message) -> None:
    """
    Функция обрабатывает ответ пользователя выводить фотографии или нет. Если да, то сколько?
    """
    response = message.text.lower()
    if response == 'да':
        keyboard = ReplyKeyboardMarkup()
        buttons = []
        for index_button in range(1, 16):
            button = KeyboardButton(text=str(index_button))
            buttons.append(button)
        keyboard.add(*buttons)
        new_message = bot.send_message(chat_id=message.chat.id,
                                       text='Укажите количество фотографий(не больше 15)',
                                       reply_markup=keyboard)
        bot.register_next_step_handler(message=new_message, callback=photo_count)
    elif response == 'нет':
        bot.send_message(chat_id=message.chat.id, text='Выполняется поиск \u23F3')
        cur_user = User.get_user(user_id=message.chat.id)
        cur_user.photo_count = 0
        print_info(message=message)
    else:
        new_message = bot.send_message(chat_id=message.chat.id, text='Некорректный ввод! Выберите да или нет')
        bot.register_next_step_handler(message=new_message, callback=check_hotel_photo)


@logger.catch
def photo_count(message: Message) -> None:
    """
    Функция котрая получает количество фотографий и проверяет корректность ввода
    """
    photos_amount = message.text
    if not photos_amount.isdigit():
        bot.send_message(chat_id=message.chat.id, text='Я вас не понимаю! Укажите количество фотографий числом')
        bot.register_next_step_handler(message=message, callback=photo_count)
        return
    elif int(photos_amount) < 1 or int(photos_amount) > 15:
        bot.send_message(chat_id=message.chat.id,
                         text='Количество фотографий не должно быть меньше 1 или превышать 15!')
        bot.send_message(chat_id=message.chat.id, text='Укажите количество фотографий(не больше 15)')
        bot.register_next_step_handler(message=message, callback=photo_count)
        return
    bot.send_message(chat_id=message.chat.id, text='Выполняется поиск \u23F3')
    cur_user = User.get_user(user_id=message.chat.id)
    cur_user.photo_count = int(photos_amount)
    print_info(message)


@logger.catch
def print_info(message: Message) -> None:
    """
    Функция выводит результат поиска отелей пользователю
    """
    cur_user = User.get_user(user_id=message.chat.id)
    command = cur_user.command
    if command == '/lowprice' or command == '/highprice':
        res = lowprice_highprice_command(user_id=message.chat.id)
    else:
        res = bestdeal_command(user_id=message.chat.id)
    photo_result = cur_user.photo_count
    if photo_result != 0:
        for keyboard, hotel, photo in res:
            try:
                bot.send_media_group(chat_id=message.chat.id, media=photo)
                bot.send_message(chat_id=message.chat.id,
                                 text=hotel,
                                 disable_web_page_preview=True,
                                 reply_markup=keyboard)
            except telebot.apihelper.ApiTelegramException:
                pass
    else:
        for keyboard, hotel in res:
            try:
                bot.send_message(chat_id=message.chat.id,
                                 text=hotel,
                                 reply_markup=keyboard)
            except telebot.apihelper.ApiTelegramException:
                pass
    Users.create(user_id=cur_user.user_id, command=cur_user.command, city_id=cur_user.city_id,
                 price_min=cur_user.price_min, price_max=cur_user.price_max,
                 check_in=cur_user.check_in, check_out=cur_user.check_out, distance_min=cur_user.distance_min,
                 distance_max=cur_user.distance_max, hotel_count=cur_user.hotel_count,
                 photo_count=cur_user.photo_count).save()


@logger.catch
@bot.message_handler(commands=['history'])
def history(message: Message) -> None:
    """
    Функция которая выводит последние запросы поиска пользователя
    """
    logger.info("User {user} used a command {command}".format(user=message.chat.id, command=message.text))
    history_info = History.select().where(History.user_id == message.chat.id).order_by(History.date_time.desc()).limit(5)
    for figure in history_info:
        bot.send_message(chat_id=message.chat.id, text=f'Команда: {figure.command}\n'
                                                       f'Время: {figure.date_time}\n'
                                                       f'Информация об отеле: {figure.hotels_info}\n')
    for i in history_info:
        print(i.command, i.date_time, i.hotels_info)


if __name__ == '__main__':
    bot.infinity_polling()
