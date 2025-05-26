from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                            InlineKeyboardMarkup, InlineKeyboardButton, 
                            )

from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


main = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='4')],
                                     [KeyboardButton(text='3')]])

three = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='РУС+МАТ+ИНФ', callback_data='inf')],
                                              [InlineKeyboardButton(text='РУС+МАТ+ФИЗ', callback_data='fiz')]])

four = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='РУС+МАТ+ИНФ+ФИЗ', callback_data='inffiz')]])


university_keyboard = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="МГУ")],
            [KeyboardButton(text="ВШЭ")],
            [KeyboardButton(text="Физтех")]],resize_keyboard=True)


