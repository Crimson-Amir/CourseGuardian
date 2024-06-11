from utilities import handle_error, main_page_keyboard, check_join_in_channel, user_manager, database_pool
import create_database
create_database.create()
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, ChatJoinRequestHandler)
from private import telegram_bot_token, ADMIN_CHAT_IDs, bot_username, sponser_channel_ids
from user.userManager import IsUserExist, RegisterUser
from admin_panel import (admin_page, add_admin, add_course_page, cource_handler, update_course_handler,
                         admin_change, admin_remove_course, admin_manage_course, admin_all_course, add_discount_code)
from wallet.wallet_telegram import (wallet_page, add_credit_to_wallet, charge_wallet_handler, credit_charge,
                                    apply_card_pay_credit, add_discount_code_handler)
from course import send_course_to_user, view_course, course_page, join_request, buy_course


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


@handle_error
async def check_join_to_channel(update, context):
    user_detail = update.effective_chat
    query = update.callback_query
    for sponser_channel_username, sponser_channel_address in sponser_channel_ids.items():
        member = await context.bot.get_chat_member(sponser_channel_address[0], user_detail.id)
        if member.status in ['left', 'kicked']:
            await query.answer('شما در کانال ها عضو نیستید!')
            return
    return await callback_main_menu(update, context)


@check_join_in_channel
async def callback_main_menu(update, context):
    query = update.callback_query
    text = '<b>درود، به ربات ما خوش آمدید.\n\nلطفا بخش مورد نظر خودتون رو انتخاب کنید:</b>'
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(main_page_keyboard), parse_mode='html')


@check_join_in_channel
async def send_main_menu(update, context):
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.delete_message()

    user_detail = update.effective_chat
    text = '<b>درود، به ربات ما خوش آمدید.\n\nلطفا بخش مورد نظر خودتون رو انتخاب کنید:</b>'
    await context.bot.send_message(chat_id=user_detail.id, text=text, reply_markup=InlineKeyboardMarkup(main_page_keyboard), parse_mode='html')


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_detail = update.effective_chat
    is_user_exist = await user_manager.execute(IsUserExist, value=user_detail.id)
    if is_user_exist[0]:
        await send_main_menu(update, context)
    else:
        refral_link = context.args[0] if context.args else None
        create_new_user = await user_manager.execute(RegisterUser, user_detail=user_detail, referral_link=refral_link)
        await send_main_menu(update, context)
        await context.bot.send_message(ADMIN_CHAT_IDs[0], f'New Start Bot.\n{create_new_user}')


@check_join_in_channel
async def referral_page(update, context):
    user_detail = update.effective_chat
    query = update.callback_query
    text = '<b>شما تا به حال کسی را به ربات دعوت نکرده اید!\n\nاز طریق لینک زیر دوستانتان را به ربات دعوت کنید:</b>'

    is_user_exist = database_pool.execute('query', {'query': f'SELECT number_of_invitations FROM UserDetail WHERE userID = {user_detail.id}'})
    get_user_referral_code = await user_manager.execute(IsUserExist, value=user_detail.id, column='referral_link')

    if is_user_exist:
        if is_user_exist[0][0]:
            text = f'<b>شما {is_user_exist[0][0]} نفر را به ربات ما دعوت کردید.</b>\n'

    referral_link = get_user_referral_code[1][0][0]
    link = f'https://t.me/{bot_username}/?start={referral_link}'

    keyboard = [[InlineKeyboardButton("ارسال برای دوستان", url=f'https://t.me/share/url?text={link}')],
                [InlineKeyboardButton('برگشت', callback_data='callback_main_menu')]]
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='html')


if __name__ == '__main__':
    application = ApplicationBuilder().token(telegram_bot_token).build()

    # User Handler
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(referral_page, pattern='referral_page'))
    application.add_handler(CallbackQueryHandler(callback_main_menu, pattern='callback_main_menu'))
    application.add_handler(CallbackQueryHandler(check_join_to_channel, pattern='check_join_to_channel'))
    application.add_handler(CallbackQueryHandler(send_main_menu, pattern='send_main_menu'))

    # wallet Handler
    application.add_handler(charge_wallet_handler)
    application.add_handler(credit_charge)
    application.add_handler(add_discount_code_handler)

    application.add_handler(CallbackQueryHandler(apply_card_pay_credit, pattern='accept_card_pay_credit_'))
    application.add_handler(CallbackQueryHandler(apply_card_pay_credit, pattern='refuse_card_pay_credit_'))
    application.add_handler(CallbackQueryHandler(apply_card_pay_credit, pattern='ok_card_pay_credit_'))
    application.add_handler(CallbackQueryHandler(apply_card_pay_credit, pattern='ok_card_pay_credit_accept_'))
    application.add_handler(CallbackQueryHandler(apply_card_pay_credit, pattern='ok_card_pay_credit_refuse_'))
    application.add_handler(CallbackQueryHandler(wallet_page, pattern='wallet_page'))
    application.add_handler(CallbackQueryHandler(add_credit_to_wallet, pattern='add_credit_to_wallet'))

    # course Handler
    application.add_handler(CallbackQueryHandler(send_course_to_user, pattern='send_course_to_user_(.*)'))
    application.add_handler(CallbackQueryHandler(buy_course, pattern='buy_course_(.*)'))
    application.add_handler(CallbackQueryHandler(view_course, pattern='view_course_(.*)'))
    application.add_handler(CallbackQueryHandler(course_page, pattern='course_list_(.*)'))
    application.add_handler(ChatJoinRequestHandler(join_request))

    # Admin Handler
    application.add_handler(CallbackQueryHandler(add_course_page, pattern='admin_add_course_page'))
    application.add_handler(cource_handler)
    application.add_handler(add_discount_code)
    application.add_handler(update_course_handler)
    application.add_handler(CommandHandler('admin', admin_page))
    application.add_handler(CommandHandler('add_admin', add_admin))
    application.add_handler(CallbackQueryHandler(admin_remove_course, pattern='admin_remove_course_'))
    application.add_handler(CallbackQueryHandler(admin_change, pattern='admin_change'))
    application.add_handler(CallbackQueryHandler(admin_manage_course, pattern='admin_manage_course_'))
    application.add_handler(CallbackQueryHandler(admin_all_course, pattern='admin_course_manag'))
    application.add_handler(CallbackQueryHandler(admin_page, pattern='admin'))

    application.run_polling()

