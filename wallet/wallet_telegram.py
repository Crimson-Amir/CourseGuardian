import telegram.error
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utilities import check_join_in_channel, user_manager, handle_error, handle_telegram_conversetion_exceptions, database_pool
from user.userManager import IsUserExist
from private import minimum_price_allowed_to_charge_wallet, maximum_price_allowed_to_charge_wallet
from telegram.ext import ConversationHandler, MessageHandler, filters, CallbackQueryHandler

GET_PRICE = 0

@handle_error
@check_join_in_channel
async def wallet_page(update, context):
    query = update.callback_query
    user_detail = update.effective_chat
    try:
        fetch_from_db = await user_manager.execute(IsUserExist, column='credit', value=user_detail.id)
        add_course_page_keyboard = []

        if fetch_from_db[0]:
            credit = fetch_from_db[1][0][0]
            text = ('<b>اطلاعات کیف پول شما:</b>'
                    f'\n\n• موجودی حساب: {credit:,} تومان')
            add_course_page_keyboard.extend([
                [InlineKeyboardButton('تازه سازی ↻', callback_data='wallet_page'),
                 InlineKeyboardButton('افزایش اعتبار ⤒', callback_data='add_credit_to_wallet')],
            ])
        else:
            text = 'متاسفانه مشکلی وجود داشت!'
        add_course_page_keyboard.append([InlineKeyboardButton('برگشت', callback_data='callback_main_menu')])

        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(add_course_page_keyboard), parse_mode='html')
    except telegram.error.BadRequest as e:
        if 'Message is not modified: specified new message content and reply markup are exactly the same' in str(e):
            await query.answer()
            return
        await query.answer('متاسفانه مشکلی وجود داشت')
        raise e
    except Exception as e:
        raise e


@handle_telegram_conversetion_exceptions
async def add_credit_to_wallet(update, context):
    query = update.callback_query
    text = ('اعتباری که میخواهید به کیف پول اضافه کنید را به تومان وارد کنید.'
            f'\n\nحداقل: {minimum_price_allowed_to_charge_wallet:,} تومن'
            f'\nحداکثر: {maximum_price_allowed_to_charge_wallet:,} تومن')
    keyboard = [[InlineKeyboardButton('برگشت', callback_data='callback_main_menu')]]
    await query.edit_message_text(text=text, parse_mode='html', reply_markup=InlineKeyboardMarkup(keyboard))
    return GET_PRICE


@handle_telegram_conversetion_exceptions
async def get_price_and_process(update, context):
    chat_id = update.effective_chat.id
    get_price = int(update.message.text.replace(',', ''))

    if minimum_price_allowed_to_charge_wallet > get_price or get_price > maximum_price_allowed_to_charge_wallet:
        text = ('ورودی نادرست است!'
                f'\n\nحداقل: {minimum_price_allowed_to_charge_wallet:,} تومن'
                f'\nحداکثر: {maximum_price_allowed_to_charge_wallet:,} تومن')
        keyboard = [[InlineKeyboardButton('کیف پول 👝', callback_data='wallet_page')]]
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='html')
        return

    database_pool.execute('transaction', [
        {'query': 'INSERT INTO Invoice (user_ID, amount, payment_for, payment_status) VALUES (%s, %s, %s, %s) RETURNING *',
         'params': (chat_id, get_price, 'charge_wallet', 'unpay')}])

    keyboard = [[InlineKeyboardButton('درگاه پرداخت پی استار', callback_data='not_ready_yet')],
        [InlineKeyboardButton('صفحه اصلی', callback_data='send_main_menu')]]

    await context.bot.send_message(chat_id=chat_id, text=f"<b>بسیار خب، لطفا روش پرداخت را انتخاب کنید:\n\nمبلغ: {get_price:,}</b>",
                                   reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='html')
    return ConversationHandler.END


charge_wallet_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(add_credit_to_wallet, pattern=r'add_credit_to_wallet')],
    states={
        GET_PRICE: [MessageHandler(filters.ALL, get_price_and_process)]
    },
    fallbacks=[],
    per_chat=True,
    allow_reentry=True,
    conversation_timeout=1500,
)
