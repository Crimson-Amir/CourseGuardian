from datetime import datetime, timedelta

import telegram.error
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from wallet.wallet_core import WalletManage
from utilities import check_join_in_channel, handle_error, database_pool

# accept_join_request = {}
wallet_manager = WalletManage('UserDetail', 'credit', database_pool, 'userID')

@handle_error
@check_join_in_channel
async def course_page(update, context):
    query = update.callback_query
    chat_id = query.message.chat_id
    number_in_page = 10
    data = query.data.replace('course_list_', '')

    get_limit = int(data) if data else number_in_page
    get_all_course = database_pool.execute('query', {'query': f'SELECT courseID,title FROM Course WHERE status = TRUE'})

    get_course = get_all_course[get_limit - number_in_page:get_limit]

    if get_course:
        keyboard = [[InlineKeyboardButton(course[1], callback_data=f"view_course_{course[0]}")] for course in get_course]

        if len(get_all_course) > number_in_page:
            keyboard_backup = []
            keyboard_backup.append(InlineKeyboardButton("قبل ⤌", callback_data=f"my_service{get_limit - number_in_page}")) if get_limit != number_in_page else None
            keyboard_backup.append(InlineKeyboardButton(f"صفحه {int(get_limit / number_in_page)}", callback_data="just_for_show"))
            keyboard_backup.append(InlineKeyboardButton("⤍ بعد", callback_data=f"my_service{get_limit + number_in_page}")) if get_limit < len(get_all_course) else None
            keyboard.append(keyboard_backup)

        keyboard.append([InlineKeyboardButton("برگشت", callback_data="callback_main_menu")])
        text = "<b>برای مشاهده جزئیات، دوره مورد نظر را انتخاب کنید:</b>"
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='html')
        except telegram.error.BadRequest:
            await query.answer('در یک پیام جدید فرستادم!')
            await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='html')

    else:
        keyboard = [[InlineKeyboardButton("برگشت", callback_data="send_main_menu")]]
        await query.edit_message_text('<b>• دوره ای وجود ندارد!</b>', parse_mode='html', reply_markup=InlineKeyboardMarkup(keyboard))


@handle_error
@check_join_in_channel
async def view_course(update, context):
    chat_id = update.effective_chat.id
    query = update.callback_query
    course_id = query.data.replace('view_course_', '')

    get_course_detail = database_pool.execute('query', {'query': f'SELECT e1.title,e1.content_type,e1.description,e1.referral_requirement,e1.price,'
                                                                 f'e1.discount_percent,e2.number_of_invitations,e2.membership_status,e1.cover_type,e1.cover,e1.discount_percent_per_invite '
                                                                 f'FROM Course e1 JOIN UserDetail e2 ON e2.userId = {chat_id} '
                                                                 f'WHERE courseID = {course_id} AND status = TRUE'})[0]

    if get_course_detail:
        referral_requirement_text, percent_per_invite, user_invite = '', '', 0

        if (get_course_detail[6] >= get_course_detail[3] != 0) or get_course_detail[7] == 'free' or int(get_course_detail[4]) == 0:
            price = 0

        else:
            if get_course_detail[10] != 0:
                user_invite = int(get_course_detail[6])
                percent_per_invite = f'\n\nشما به ازای هر دعوت یک درصد تخفیف میگیرید\nتعداد دعوت های شما: {user_invite}'

            price = round(int(get_course_detail[4] - (int(get_course_detail[4]) * min((int(get_course_detail[5]) + user_invite), 100) / 100)), -2)

        if price:
            string_price = f'{price:,} تومان'
            keyboard = [[InlineKeyboardButton("دریافت دوره", callback_data=f"buy_course_{course_id}_{price}")]]
        else:
            string_price = 'رایگان برای شما'
            keyboard = [[InlineKeyboardButton("دریافت رایگان دوره", callback_data=f"send_course_to_user_{course_id}_{price}")]]


        if get_course_detail[3] != 0:
            referral_requirement_text = (f'\n\n{get_course_detail[3]} نفر را به ربات دعوت کنید تا این دوره را رایگان دریافت کنید!'
                                         f'\nتعداد دعوت های شما: {get_course_detail[6]}')

        keyboard.append([InlineKeyboardButton("برگشت", callback_data="course_list_")])

        discount = f'\nتخفیف: {get_course_detail[5]} درصد' if get_course_detail[5] else ''
        text = (f"نام دوره: {get_course_detail[0]}"
                f"\n\nتوضیحات:\n {get_course_detail[2]}"
                f"\n\nقیمت: {string_price}"
                f"{discount}"
                f"{referral_requirement_text}"
                f"{percent_per_invite}")

        cover_type = get_course_detail[8]
        cover = get_course_detail[9].tobytes()

        try:
            if cover_type == 'photo':
                await query.delete_message()
                await context.bot.send_photo(chat_id, photo=cover, caption=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='html')
            elif cover_type == 'video':
                await query.delete_message()
                await context.bot.send_video(chat_id, video=cover, caption=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='html')
            else:
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='html')

        except Exception as e:
            print(e)
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='html')
    else:
        await query.edit_message_text('<b>• این دوره در دسترس نیست!</b>', parse_mode='html')


@handle_error
@check_join_in_channel
async def buy_course(update, context):
    query = update.callback_query
    await query.delete_message()
    chat_id = update.effective_chat.id
    data = query.data.replace('buy_course_', '').split('_')
    course_id = data[0]
    price = int(data[1])
    credit = await wallet_manager.get_wallet_credit(chat_id)

    if price > credit:
        text = ('اعتبار کیف پول شما برای دریافت این دوره کافی نیست!'
                f'\n\nاعتبار کیف پول: {credit:,} تومان'
                '\n\nدرصورت تمایل اعتبار خود را افزایش دهید')

        keyboard = [[InlineKeyboardButton('کیف پول 👝', callback_data='wallet_page')],
                    [InlineKeyboardButton("برگشت", callback_data="course_list_")]]

        await context.bot.send_message(chat_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='html')
        return

    else:
        text = ('اطلاعات زیر را بررسی کنید و درصورت تایید پرداخت را انجام دهید.'
                f'\n\nقیمت دوره: {price:,} تومان'
                f'\nاعتبار کیف پول: {credit:,} تومان')

        keyboard = [[InlineKeyboardButton("دریافت دوره", callback_data=f"send_course_to_user_{course_id}_{price}")],
                    [InlineKeyboardButton("برگشت", callback_data="course_list_")]]

        await context.bot.send_message(chat_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='html')
        return


@handle_error
@check_join_in_channel
async def send_course_to_user(update, context):
    query = update.callback_query
    chat_id = update.effective_chat.id
    data = query.data.replace('send_course_to_user_', '').split('_')
    course_id = data[0]
    price = int(data[1])
    allow_time_in_min = 30

    if price != 0:
        credit = await wallet_manager.get_wallet_credit(chat_id)
        if price > credit:
            await context.bot.send_message(chat_id=chat_id, text='اعتبار شما برای دریافت این دوره کافی نیست!')
            return
        less_from_wallet = await wallet_manager.less_from_wallet(chat_id, price)
        if not less_from_wallet:
            await context.bot.send_message(chat_id=chat_id, text='مشکلی در کسر اعتبار وجود داشت!')
            return

    get_course_detail = database_pool.execute('query', {'query': f'SELECT content_type,media,channel_link,channel_chat_id FROM Course' f' WHERE courseID = {course_id} AND status = TRUE'})[0]

    if get_course_detail:
        course_type = get_course_detail[0]
        if course_type == 'chennel_link':
            # accept_join_request[chat_id] = {'time': datetime.now(), 'period': timedelta(minutes=allow_time_in_min), 'channel_chat_id': get_course_detail[3]}

            database_pool.execute('transaction', [{'query': 'INSERT INTO Accept_Private_Channel(status, user_ID, course_ID, period_minut, channel_chat_id) VALUES (%s,%s,%s,%s) RETURNING *',
                                                   'params': (True, chat_id, course_id, allow_time_in_min, get_course_detail[3])}])

            keyboard = [
                [InlineKeyboardButton("لینک کانال", url=get_course_detail[2])],
                [InlineKeyboardButton("صفحه اصلی", callback_data='send_main_menu')]
            ]
            text = f'از طریق لینک زیر میتوانید داخل کانال جوین بشید.\n\nمعتبر تا {allow_time_in_min} دقیقه'
            await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard))
            return

        elif course_type == 'text':
            await context.bot.send_message(chat_id, text=get_course_detail[1].tobytes().decode('utf-8')[:4095])

        elif course_type == 'document':
            await context.bot.send_document(chat_id, document=get_course_detail[1].tobytes())

        elif course_type == 'image':
            await context.bot.send_photo(chat_id, photo=get_course_detail[1].tobytes())

        elif course_type == 'video':
            await context.bot.send_video(chat_id, video=get_course_detail[1].tobytes())

        elif course_type == 'voice':
            await context.bot.send_voice(chat_id, voice=get_course_detail[1].tobytes())

        keyboard = [[InlineKeyboardButton("صفحه اصلی", callback_data='callback_main_menu')]]

        text = 'دوره برای شما فرستاده شد!'
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='html')
    else:
        await query.edit_message_text('<b>• این دوره در دسترس نیست!</b>', parse_mode='html')


async def join_request(update, context):
    get_all_join_accept = database_pool.execute('query', {'query': f'SELECT id,created_at,period_minut,user_ID,channel_chat_id FROM Accept_Private_Channel WHERE status = TRUE'})

    if get_all_join_accept:
        for accept_request in get_all_join_accept[0]:
            is_alive = datetime.now() > (accept_request[1] + timedelta(minutes=accept_request[2]))
            if is_alive:
                database_pool.execute('transaction', [{'query': f'UPDATE Accept_Private_Channel SET status = FALSE  WHERE userID = {accept_request[0]} RETURNING *', 'params': None}])
                continue
            try:
                await context.bot.approve_chat_join_request(chat_id=str(accept_request[4]), user_id=str(accept_request[3]))
            except Exception as e:
                print(e)
                pass

