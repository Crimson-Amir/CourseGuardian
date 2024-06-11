import datetime

import telegram.error
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utilities import (check_join_in_channel, user_manager, handle_error, handle_telegram_conversetion_exceptions,
                       database_pool, wallet_manager, handle_telegram_exceptions_without_user_side)
from user.userManager import IsUserExist
from private import minimum_price_allowed_to_charge_wallet, maximum_price_allowed_to_charge_wallet, card_detail, ADMIN_CHAT_IDs
from telegram.ext import ConversationHandler, MessageHandler, filters, CallbackQueryHandler


GET_DISCOUNT_CODE = 0
GET_PRICE = 0
GET_EVIDENCE_CREDIT = 0
factor_time_in_sec = 600

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
    get_price = int(update.message.text.replace(',',''))

    if minimum_price_allowed_to_charge_wallet > get_price or get_price > maximum_price_allowed_to_charge_wallet:
        text = ('ورودی نادرست است!'
                f'\n\nحداقل: {minimum_price_allowed_to_charge_wallet:,} تومن'
                f'\nحداکثر: {maximum_price_allowed_to_charge_wallet:,} تومن')
        keyboard = [[InlineKeyboardButton('کیف پول 👝', callback_data='wallet_page')]]
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='html')
        return

    invoice_id = database_pool.execute('transaction', [
        {'query': 'INSERT INTO Invoice (userID, amount, payment_for, payment_status) VALUES (%s, %s, %s, %s) RETURNING invoiceID',
         'params': (chat_id, get_price, 'charge_wallet', 'unpay')}])[0][0][0]

    context.user_data['price'] = get_price
    context.user_data['invoice_id'] = invoice_id

    keyboard = [[InlineKeyboardButton('کارت به کارت', callback_data=f'pay_by_card_for_credit_{get_price}_{invoice_id}')],
                [InlineKeyboardButton('اضافه کردن کد تخفیف', callback_data=f'add_discount_code_{get_price}_{invoice_id}')],
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


@handle_telegram_conversetion_exceptions
async def add_discount_code(update, context):
    query = update.callback_query
    query.delete_message()
    text = 'کد تخفیف خودتون رو وارد کنید'
    await query.edit_message_text(text=text, parse_mode='html', reply_markup=InlineKeyboardMarkup([]))
    return GET_DISCOUNT_CODE


@handle_telegram_conversetion_exceptions
async def get_discount_code(update, context):
    chat_id = int(update.effective_chat.id)
    get_price = context.user_data['price']
    invoice_id = context.user_data['invoice_id']
    discount_code = update.message.text

    get_discount_code_detail = database_pool.execute('query', {'query': f'SELECT is_active,available_for_all_user,for_userID,credit,valid_until,discountID,code FROM DiscountCode WHERE code = %s', 'params': (discount_code,)})

    if not get_discount_code_detail:
        await context.bot.send_message(chat_id=chat_id,text=f"<b>کد تخفیف وجود ندارد!</b>",parse_mode='html')
        return ConversationHandler.END

    if not get_discount_code_detail[0][0]:
        await context.bot.send_message(chat_id=chat_id,text=f"<b>کد تخفیف فعال نیست!</b>",parse_mode='html')
        return ConversationHandler.END

    if datetime.datetime.now() > get_discount_code_detail[0][4]:
        await context.bot.send_message(chat_id=chat_id,text=f"<b>کد تخفیف منقضی شده است!</b>",parse_mode='html')
        return ConversationHandler.END

    discount_credit = get_discount_code_detail[0][3]

    is_user_use_discount = database_pool.execute('query', {
        'query': f'SELECT usediscountID FROM UseDiscount WHERE discountID = %s AND userID = %s',
        'params': (get_discount_code_detail[0][5], chat_id)})

    print(get_discount_code_detail)

    if not is_user_use_discount:

        if get_discount_code_detail[0][1]:
            get_price = max(int(get_price - int(discount_credit)), 0)
            context.user_data['price'] = get_price

        else:
            for user in get_discount_code_detail:
                if user[2] == chat_id and user[6] == discount_code:
                    get_price = max(int(get_price - int(discount_credit)), 0)
                    context.user_data['price'] = get_price
                    break

        database_pool.execute('transaction', [
            {'query': f'UPDATE Invoice SET amount = %s,discount = %s,discountID = %s WHERE invoiceID = {invoice_id}',
             'params': (get_price, discount_credit, get_discount_code_detail[0][5])}])

        keyboard = [
            [InlineKeyboardButton('کارت به کارت', callback_data=f'pay_by_card_for_credit_{get_price}_{invoice_id}')],
            [InlineKeyboardButton('صفحه اصلی', callback_data='send_main_menu')]]

        await context.bot.send_message(chat_id=chat_id,
                                       text=f"<b>{discount_credit:,} تومان تخفیف با موفقیت اعمال شد، لطفا روش پرداخت را انتخاب کنید:\n\nمبلغ: {get_price:,}</b>",
                                       reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='html')

    else:
        await context.bot.send_message(chat_id=chat_id, text=f"<b>شما قبلا از این کد استفاده کردید!</b>", parse_mode='html')

    return ConversationHandler.END



add_discount_code_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(add_discount_code, pattern=r'add_discount_code_(.*)')],
    states={
        GET_DISCOUNT_CODE: [MessageHandler(filters.TEXT, get_discount_code)]
    },
    fallbacks=[],
    per_chat=True,
    allow_reentry=True,
    conversation_timeout=1500,
)



@handle_telegram_conversetion_exceptions
async def pay_by_card_for_credit(update, context):
    query = update.callback_query
    price = context.user_data['price']
    keyboard = [[InlineKeyboardButton("صفحه اصلی ⤶", callback_data="send_main_menu")]]

    text = (f"\n\nمدت اعتبار فاکتور: {factor_time_in_sec / 60} دقیقه"
            f"\n*قیمت*: `{price:,}`* تومان *"
            f"\n\n*• لطفا مبلغ رو به شماره‌حساب زیر واریز کنید و اسکرین‌شات یا شماره‌پیگیری رو بعد از همین پیام ارسال کنید، اطمینان حاصل کنید ربات درخواست رو ثبت کنه.*"
            f"\n\n{card_detail}"
            f"\n\n*• بعد از تایید شدن پرداخت، سرویس برای شما ارسال میشه، زمان تقریبی 5 دقیقه الی 3 ساعت.*")

    await context.bot.send_message(chat_id=query.message.chat_id, text=text, parse_mode='markdown',
                                   reply_markup=InlineKeyboardMarkup(keyboard))
    await query.answer('فاکتور برای شما ارسال شد.')
    return GET_EVIDENCE_CREDIT


@handle_telegram_conversetion_exceptions
async def pay_by_card_for_credit_admin(update, context):
    user = update.message.from_user
    price = context.user_data['price']
    invoice_id = context.user_data['invoice_id']

    keyboard = [[InlineKeyboardButton("قبول کردن ✅", callback_data=f"accept_card_pay_credit_{invoice_id}"),
                 InlineKeyboardButton("رد کردن ❌", callback_data=f"refuse_card_pay_credit_{invoice_id}")],
                [InlineKeyboardButton("پنهان کردن دکمه ها", callback_data=f"hide_buttons")]]

    text_ = f'<b>درخواست شما با موفقیت ثبت شد✅\nنتیجه از طریق همین ربات بهتون اعلام میشه</b>'
    text = "درخواست کارت به کارت را بررسی کنید:\n\n"

    text += f"نام: {user['first_name']}\nیوزرنیم: @{user['username']}\nچت آیدی: {user['id']}\n\n"

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        text += f"کپشن: {update.message.caption}" or 'بدون کپشن!'
        text += f"\n\nقیمت: {price:,} T"
        await context.bot.send_photo(chat_id=ADMIN_CHAT_IDs[0], photo=file_id, caption=text, reply_markup=InlineKeyboardMarkup(keyboard))
        await update.message.reply_text(text_, parse_mode='html')
    elif update.message.text:
        text += f"متن: {update.message.text}\n\nقیمت: {price:,} T"
        await context.bot.send_message(chat_id=ADMIN_CHAT_IDs[0], text=text, reply_markup=InlineKeyboardMarkup(keyboard))
        await update.message.reply_text(text_, parse_mode='html')
    else:
        await update.message.reply_text('مشکلی وجود داره!')

    context.user_data.clear()
    return ConversationHandler.END


credit_charge = ConversationHandler(
    entry_points=[CallbackQueryHandler(pay_by_card_for_credit, pattern=r'pay_by_card_for_credit_\d+')],
    states={
        GET_EVIDENCE_CREDIT: [MessageHandler(filters.ALL, pay_by_card_for_credit_admin)]
    },
    fallbacks=[],
    conversation_timeout=1000,
    per_chat=True,
    allow_reentry=True
)

@handle_telegram_exceptions_without_user_side
async def add_credit_to_wallet_func(context, invoice_id):
    get_invoice = database_pool.execute('query', {'query': f'SELECT userID,amount,discountID FROM Invoice WHERE invoiceID = %s', 'params': (invoice_id,)})

    if get_invoice:
        if get_invoice[0][2]:
            database_pool.execute('transaction', [
                {'query': 'INSERT INTO UseDiscount (discountID, userID) VALUES (%s, %s)',
                 'params': (get_invoice[0][2], get_invoice[0][0])}])

        add_to_wallet = await wallet_manager.add_to_wallet(get_invoice[0][0], get_invoice[0][1])
        if not add_to_wallet:
            raise ValueError(f'problem in add credit to wallet')
        finish_invoice = database_pool.execute('transaction', [{'query': 'UPDATE Invoice SET payment_status = %s, payment_method = %s WHERE invoiceID = %s RETURNING userID,amount',
                                                                'params': ("pay", "card_to_card", invoice_id)}])[0]
        await context.bot.send_message(ADMIN_CHAT_IDs[0], '🟢 عملیات کیف پول موفقیت آمیز بود')
        return finish_invoice

    raise ValueError(f'there is no invoice with {invoice_id} id')


@handle_error
async def apply_card_pay_credit(update, context):
    query = update.callback_query

    if 'accept_card_pay_credit_' in query.data or 'refuse_card_pay_credit_' in query.data:
        data = query.data.replace('card_pay_credit_', '').split('_')
        status = data[0]
        invoice_id = data[1]
        keyboard = [[InlineKeyboardButton("بله", callback_data=f"ok_card_pay_credit_{status}_{invoice_id}")],
                    [InlineKeyboardButton("خیر", callback_data=f"cancel_pay")]]
        await query.answer('لطفا تایید کنید!')
        await context.bot.send_message(text='از تایید تراکنش مطمئنید؟', reply_markup=InlineKeyboardMarkup(keyboard), chat_id=ADMIN_CHAT_IDs[0])

    elif 'ok_card_pay_credit_accept_' in query.data:
        invoice_id = int(query.data.replace('ok_card_pay_credit_accept_', ''))
        invoice_detail = await add_credit_to_wallet_func(context, invoice_id)

        await context.bot.send_message(text=f'مبلغ {invoice_detail[0][1]:,} تومن با موفقیت به کیف پول شما اضافه شد ✅', chat_id=invoice_detail[0][0])
        await query.answer('Done ✅')
        await query.delete_message()

    elif 'ok_card_pay_credit_refuse_' in query.data:
        invoice_id = int(query.data.replace('ok_card_pay_credit_refuse_', ''))
        get_invoice = database_pool.execute('query', {'query': f'SELECT userID FROM Invoice WHERE invoiceID = {invoice_id}'})[0]

        await context.bot.send_message(
            text=f'درخواست شما برای واریز به کیف پول پذیرفته نشد❌',
            chat_id=get_invoice[0])

        await query.answer('Done ✅')
        await query.delete_message()

    elif 'cancel_pay' in query.data:
        query.answer('Done ✅')
        query.delete_message()
