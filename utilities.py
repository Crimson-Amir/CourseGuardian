import requests

from private import telegram_bot_url, ADMIN_CHAT_IDs, sponser_channel_ids, database_detail
import functools
import arrow
from datetime import datetime
import aiohttp
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from posgres_manager import Client
from user.userManager import UserClient
import traceback
from telegram.ext import ConversationHandler


main_page_keyboard = [
    [InlineKeyboardButton('دوره ها 📚', callback_data='course_list_')],
    [InlineKeyboardButton('کیف پول 👝', callback_data='wallet_page')],
    [InlineKeyboardButton('زیرمجموعه گیری 👥', callback_data='referral_page')]
]
database_pool = Client(**database_detail)
user_manager = UserClient(database_pool)


def report_problem_to_admin(msg: str):
    return requests.post(url=telegram_bot_url, data={'chat_id': ADMIN_CHAT_IDs[0], 'text': msg})


def handle_error(func):
    @functools.wraps(func)
    def warpper(update, context):
        user_detail = update.effective_chat
        try:
            return func(update, context)
        except Exception as e:
            err = ("🔴 Report Problem in Bot\n\n"
                    f"Something Went Wrong In <b>{func.__name__}</b> Section."
                    f"\nUser ID: {user_detail.id}"
                    f"\nError Type: {type(e).__name__}"
                    f"\nError Reason:\n{e}")

            print(err)
            report_problem_to_admin(err)
            context.bot.send_message(text='متاسفانه مشکلی وجود داشت، گزارش به ادمین ها ارسال شد!', chat_id=user_detail.id)
    return warpper


def replace_with_space(txt):
    return txt.replace('_', ' ')

def human_readable(date):
    get_date = arrow.get(date)
    return get_date.humanize()

def unix_time_to_datetime(date):
    return datetime.fromtimestamp(date)


def check_join_in_channel(func):
    async def wrapper(update, context):
        user_detail = update.effective_chat
        join_channel_button, text = [], ''
        for sponser_channel_username, sponser_channel_address in sponser_channel_ids.items():
            member = await context.bot.get_chat_member(sponser_channel_address[0], user_detail.id)
            if member.status in ['left', 'kicked']:
                text = 'شما در کانال یا گروه های زیر عضو نیستید!'
                join_channel_button.append(
                    [InlineKeyboardButton(sponser_channel_username, url=f'https://t.me/{sponser_channel_address[1]}')])
        if join_channel_button:
            join_channel_button.append([InlineKeyboardButton('عضو شدم ✅', callback_data='check_join_to_channel')])
            await context.bot.send_message(chat_id=user_detail.id, text=text,
                                           reply_markup=InlineKeyboardMarkup(join_channel_button))
            return
        return await func(update, context)

    return wrapper


async def report_problem(func_name, error, side, extra_message=None):
    text = (f"🔴 BOT Report Problem [{side}]\n\n"
            f"\nFunc Name: {func_name}"
            f"\nError Type: {type(error).__name__}"
            f"\nError Reason:\n{error}"
            f"\nExtra Message:\n{extra_message}")

    requests.post(url=telegram_bot_url, data={'chat_id': ADMIN_CHAT_IDs[0], 'text': text})


async def something_went_wrong(update, context):
    text= "متاسفانه مشکلی وجود داشت!\nگزارش مشکل به ادمین ارسال شد."
    if getattr(update, 'callback_query'):
        query = update.callback_query
        await query.answer(text)
    else:
        await update.message.reply_text(text)


def handle_telegram_exceptions(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            side = 'Telgram Func'
            print(f"[{side}] An error occurred in {func.__name__}: {e}")
            await report_problem(func.__name__, e, side, extra_message=traceback.format_exc())
            await something_went_wrong(*args)

    return wrapper


def handle_telegram_conversetion_exceptions(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            print(e)
            await report_problem(func.__name__, e, 'Telegram Conversetion Func', extra_message=traceback.format_exc())
            await something_went_wrong(*args)
            return ConversationHandler.END

    return wrapper

async def report_problem_to_admin_witout_context(text, chat_id, error, detail=None):
    text = ("🔴 Report Problem in Bot\n\n"
            f"Something Went Wrong In {text} Section."
            f"\nUser ID: {chat_id}"
            f"\nError Type: {type(error).__name__}"
            f"\nError Reason:\n{error}")

    text += f"\nDetail:\n {detail}" if detail else ''
    requests.post(url=telegram_bot_url, data={'chat_id': ADMIN_CHAT_IDs[0], 'text': text})
    print(f'* REPORT TO ADMIN SUCCESS: ERR: {error}')

