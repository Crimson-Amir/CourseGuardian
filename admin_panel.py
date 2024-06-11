import hashlib
import uuid
from datetime import datetime
from utilities import database_pool, handle_telegram_conversetion_exceptions
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import psycopg2
from private import ADMIN_CHAT_IDs
from telegram.ext import ConversationHandler, MessageHandler, filters, CallbackQueryHandler

confirm_remove_course = {}

admin_page_keyboard = [
    [InlineKeyboardButton('اضافه کردن دوره', callback_data='admin_add_course_page')],
    [InlineKeyboardButton('مدیریت دوره ها', callback_data='admin_course_manag')],
    [InlineKeyboardButton('اضافه کردن کد تخفیف', callback_data='admin_add_discount_code')]
]

(GET_TITLE, GET_DESCRIPTION, GET_COVER, GET_DISCOUNT_PERCENT_PER_INVITE, GET_DISCOUNT, GET_NUMBER_OF_REFERRAL_TO_BE_FREE,
 GET_PRICE, GET_STATUS, GET_CONTENT, PRIVATE_CHANNEL_CHAT_ID) = range(10)
EDIT_COURSE = 0
ADD_DISCOUNT_CODE_VALID_FOR_USER, ADD_DISCOUNT_CODE_CREDIT, ADD_DISCOUNT_CODE_VALID_UNTIL = range(3)

def check_is_admin(func):
    async def wrapper(update, context):
        user_detail = update.effective_chat
        is_admin = database_pool.execute('query', {'query': f'SELECT adminID FROM Admin WHERE UserID = {user_detail.id}', 'params': None})
        if is_admin or user_detail.id in ADMIN_CHAT_IDs:
            return await func(update, context)
        return
    return wrapper


@check_is_admin
async def add_admin(update, context):
    user_detail = update.effective_chat
    new_admin_user_id = context.args
    if not new_admin_user_id:
        text = 'لطفا آیدی کاربر را وارد کنید'
    else:
        try:
            database_pool.execute('transaction', [{'query': 'INSERT INTO Admin (userID) VALUES (%s) RETURNING *', 'params': (user_detail.id,)}])
            text = 'ادمین با موفقیت اضافه شد'
        except psycopg2.errors.ForeignKeyViolation as fk_error:
            text = f'عملیات موفقیت آمیز نبود.\nخطای ForeignKey: {fk_error}'
        except Exception as e:
            text = f'عملیات موفقیت آمیز نبود.\nخطا: {e}'

    await context.bot.send_message(chat_id=user_detail.id, text=text, parse_mode='html')


@check_is_admin
async def admin_page(update, context):
    user_detail = update.effective_chat
    text = '<b>درود، به پنل ادمین خوش آمدید.\n\nلطفا بخش مورد نظر خودتون رو انتخاب کنید:</b>'
    await context.bot.send_message(chat_id=user_detail.id, text=text, reply_markup=InlineKeyboardMarkup(admin_page_keyboard), parse_mode='html')


@check_is_admin
async def add_course_page(update, context):
    query = update.callback_query
    text = '<b>محتوا دوره چیست؟</b>'
    add_course_page_keyboard = [
        [InlineKeyboardButton('متن', callback_data='admin_add_course_text')],
        [InlineKeyboardButton('فایل داکیومنت', callback_data='admin_add_course_document')],
        [InlineKeyboardButton('فایل تصویری', callback_data='admin_add_course_photo')],
        [InlineKeyboardButton('فایل ویدیویی', callback_data='admin_add_course_video')],
        [InlineKeyboardButton('فایل صوتی', callback_data='admin_add_course_voice')],
        [InlineKeyboardButton('لینک کانال', callback_data='admin_add_course_chennel_link')],
        [InlineKeyboardButton('برگشت', callback_data='admin')]]
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(add_course_page_keyboard), parse_mode='html')


@handle_telegram_conversetion_exceptions
async def add_course_conversation(update, context):
    chat_id = update.effective_chat.id
    query = update.callback_query
    get_content = query.data.replace('admin_add_course_', '')
    context.user_data['course_content_type'] = get_content
    await query.answer()
    text = 'بسیار خب، عنوان دوره را بفرستید'
    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode='html')
    return GET_TITLE


@handle_telegram_conversetion_exceptions
async def get_course_title(update, context):
    chat_id = update.effective_chat.id
    context.user_data['course_title'] = update.message.text
    text = "حالا توضیحات دوره را بفرستید"
    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode='html')
    return GET_DESCRIPTION


@handle_telegram_conversetion_exceptions
async def get_course_description(update, context):
    chat_id = update.effective_chat.id
    context.user_data['course_description'] = update.message.text
    text = "کاور دوره را بفرستید، این میتواند عکس یا ویدیو باشد."
    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode='html')
    return GET_COVER


@handle_telegram_conversetion_exceptions
async def get_cover(update, context):
    chat_id = update.effective_chat.id

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        course_cover_type = 'photo'
    elif update.message.video:
        file_id = update.message.video.file_id
        course_cover_type = 'video'
    else:
        await context.bot.send_message(chat_id=chat_id, text='فرمت درست نبود، عملیات کنسل شد!', parse_mode='html')
        return ConversationHandler.END

    file = await context.bot.get_file(file_id)
    text = "حالا قیمت دوره را بفرستید، 0 اگر دوره رایگان است"


    context.user_data['course_cover_type'] = course_cover_type
    context.user_data['course_cover_file'] = file

    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode='html')

    return GET_PRICE


@handle_telegram_conversetion_exceptions
async def get_course_price(update, context):
    chat_id = update.effective_chat.id
    context.user_data['course_price'] = int(update.message.text)
    text = "کاربر باید چند نفر را به ربات دعوت کرده باشد تا این دوره را رایگان دریافت کند؟ برای غیرفعال بودن این ویژگی 0 را بفرستید."
    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode='html')
    return GET_NUMBER_OF_REFERRAL_TO_BE_FREE


@handle_telegram_conversetion_exceptions
async def get_course_number_of_referral(update, context):
    chat_id = update.effective_chat.id
    context.user_data['course_number_of_referral'] = int(update.message.text)
    text = "میخواهید کاربر به ازای هر یک دعوت یک درصد تخفیف بگیرد؟\n1 برای روشن بودن و 0 برای خاموش بود این حالت"
    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode='html')
    return GET_DISCOUNT_PERCENT_PER_INVITE


@handle_telegram_conversetion_exceptions
async def get_discount_percent_per_invite(update, context):
    chat_id = update.effective_chat.id
    context.user_data['course_discount_percent_per_invite'] = int(update.message.text)
    text = "این دوره چقدر تخفیف دارد؟ 0 برای بدون تخفیف"
    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode='html')
    return GET_DISCOUNT


@handle_telegram_conversetion_exceptions
async def get_course_discount(update, context):
    chat_id = update.effective_chat.id
    context.user_data['course_discount'] = int(update.message.text)
    text = "اگر دوره در کانال پرایوت با accept join است، آیدی چنل پرایوت را بفرستید. در غیر این صورت 0 را بفرستید."
    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode='html')
    return PRIVATE_CHANNEL_CHAT_ID


@handle_telegram_conversetion_exceptions
async def get_channel_chat_id(update, context):
    chat_id = update.effective_chat.id
    context.user_data['private_channel_chat_id'] = update.message.text
    text = "وضعیت دوره را بفرستید.\n0: غیرفعال\n1: فعال"
    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode='html')
    return GET_STATUS


@handle_telegram_conversetion_exceptions
async def get_course_status(update, context):
    chat_id = update.effective_chat.id
    user_text = update.message.text

    if int(user_text):
        status = True
    else:
        status = False
    context.user_data['course_status'] = status
    text = "حالا محتوا دوره یا لینک را بفرستید."
    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode='html')
    return GET_CONTENT


@handle_telegram_conversetion_exceptions
async def get_course_media(update, context):
    chat_id = update.effective_chat.id

    course_content_type = context.user_data['course_content_type']
    course_title = context.user_data['course_title']
    course_description = context.user_data['course_description']
    course_price = context.user_data['course_price']
    course_number_of_referral = context.user_data['course_number_of_referral']
    course_discount = context.user_data['course_discount']
    course_status = context.user_data['course_status']
    channel_chat_id = context.user_data['private_channel_chat_id']
    course_cover_type = context.user_data['course_cover_type']
    course_cover = await context.user_data['course_cover_file'].download_as_bytearray()
    discount_percent_per_invite = context.user_data['course_discount_percent_per_invite']

    file_id, media, channel_link = None, None, None
    if course_content_type == 'document':
        file_id = update.message.document.file_id
    elif course_content_type == 'photo':
        file_id = update.message.photo[-1].file_id
    elif course_content_type == 'voice':
        file_id = update.message.voice.file_id
    elif course_content_type == 'video':
        file_id = update.message.video.file_id
    elif course_content_type == 'text':
        media = update.message.text.encode('utf-8')
    elif course_content_type == 'chennel_link':
        channel_link = str(update.message.text)
    else:
        await context.bot.send_message(chat_id=chat_id, text="نوع فایل قابل قبول نیست!")
        return

    if file_id:
        file = await context.bot.get_file(file_id)
        media = await file.download_as_bytearray()

    database_pool.execute('transaction', [
        {'query': 'INSERT INTO Course (status, content_type, title, description, cover_type, cover, media, channel_link, channel_chat_id, discount_percent_per_invite, price, referral_requirement, discount_percent) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *',
         'params': (course_status, course_content_type, course_title, course_description, course_cover_type, course_cover, media, channel_link, channel_chat_id, discount_percent_per_invite, course_price, course_number_of_referral, course_discount)}])

    await context.bot.send_message(chat_id=chat_id, text="دوره با موفقیت ذخیره شد!")
    return ConversationHandler.END


cource_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(add_course_conversation, pattern=r'admin_add_course_(.*)')],
    states={
        GET_TITLE: [MessageHandler(filters.TEXT, get_course_title)],
        GET_DESCRIPTION: [MessageHandler(filters.TEXT, get_course_description)],
        GET_COVER: [MessageHandler(filters.ALL, get_cover)],
        GET_PRICE: [MessageHandler(filters.TEXT, get_course_price)],
        GET_NUMBER_OF_REFERRAL_TO_BE_FREE: [MessageHandler(filters.TEXT, get_course_number_of_referral)],
        GET_DISCOUNT_PERCENT_PER_INVITE: [MessageHandler(filters.TEXT, get_discount_percent_per_invite)],
        GET_DISCOUNT: [MessageHandler(filters.TEXT, get_course_discount)],
        PRIVATE_CHANNEL_CHAT_ID: [MessageHandler(filters.TEXT, get_channel_chat_id)],
        GET_STATUS: [MessageHandler(filters.TEXT, get_course_status)],
        GET_CONTENT: [MessageHandler(filters.ALL, get_course_media)]
    },
    fallbacks=[],
    per_chat=True,
    allow_reentry=True,
    conversation_timeout=1500,
)


@check_is_admin
async def admin_all_course(update, context):
    query = update.callback_query
    text = '<b>دوره مورد نظر را انتخاب کنید:</b>'
    get_all_course = database_pool.execute('query', {'query': f'SELECT courseID,title FROM Course'})
    add_course_page_keyboard = [[InlineKeyboardButton(course[1], callback_data=f'admin_manage_course_{course[0]}')] for course in get_all_course]
    add_course_page_keyboard.append([InlineKeyboardButton('برگشت', callback_data='admin')])
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(add_course_page_keyboard), parse_mode='html')


@check_is_admin
async def admin_manage_course(update, context):
    chat_id = update.effective_chat.id
    query = update.callback_query
    course_id = query.data.replace('admin_manage_course_', '')

    get_course_detail = database_pool.execute('query', {'query': f'SELECT title,content_type,description,referral_requirement,price,'
                                                                 f'discount_percent,cover_type,cover,discount_percent_per_invite '
                                                                 f'FROM Course WHERE courseID = {course_id}'})[0]

    if get_course_detail:
        keyboard = [
            [InlineKeyboardButton("دریافت دوره", callback_data=f"send_course_to_user_{course_id}_0")],
            [InlineKeyboardButton("تغییر تایتل", callback_data=f"admin_change&title&{course_id}"),
             InlineKeyboardButton("تغییر توضیحات", callback_data=f"admin_change&description&{course_id}")],
            [InlineKeyboardButton("تغییر رفرال موردنیاز برای دریافت رایگان", callback_data=f"admin_change&referral_requirement&{course_id}")],
            [InlineKeyboardButton("تغییر قیمت", callback_data=f"admin_change&price&{course_id}"),
             InlineKeyboardButton("تغییر نوع کاور", callback_data=f"admin_change&cover_type&{course_id}")],
            [InlineKeyboardButton("تغییر کاور", callback_data=f"admin_change&cover&{course_id}")],
            [InlineKeyboardButton("تغییر درصد تخفیف", callback_data=f"admin_change&discount_percent&{course_id}")],
            [InlineKeyboardButton("تغییر وضعیت تخفیف به ازای اینوایت", callback_data=f"admin_change&discount_percent_per_invite&{course_id}")],
            [InlineKeyboardButton("تغییر نوع محتوا (text, document, photo, video, voice)", callback_data=f"admin_change&content_type&{course_id}")],
            [InlineKeyboardButton("تغییر محتوا", callback_data=f"admin_change&media&{course_id}")],
            [InlineKeyboardButton("تغییر لینک چنل پرایوت", callback_data=f"admin_change&channel_link&{course_id}"),
             InlineKeyboardButton("تغییر آیدی چنل پرایوت", callback_data=f"admin_change&channel_chat_id&{course_id}")],
            [InlineKeyboardButton("تغییر وضعیت نمایش (True or False)", callback_data=f"admin_change&status&{course_id}")],
            [InlineKeyboardButton("حذف دوره", callback_data=f"admin_remove_course_{course_id}")],
            [InlineKeyboardButton("برگشت", callback_data="course_list_")]]

        text = (f"نام دوره: {get_course_detail[0]}"
                f"\n\nتوضیحات:\n {get_course_detail[2]}"
                f"\n\nقیمت: {get_course_detail[4]:,}"
                f"\nتخفیف: {get_course_detail[5]}"
                f"\nنوع محتوا: {get_course_detail[1]}"
                f"\nتعداد رفرال مورد نیاز برای رایگان بودن دوره: {get_course_detail[3]}"
                f"\nمدل کاور: {get_course_detail[6]}"
                f"\nفعال بودن یک درصد تخفیف به ازای هر اینوایت: {get_course_detail[8]}"
                f"\n\nاگر کاور شما درحال حاضر ویدیو است و میخواهید آن را تبدیل به عکس کنید، ابتدا با گزینه تغییر نوع کاور این کار را انجام دهید. ورودی های مجاز photo و video است."
                )

        cover_type = get_course_detail[6]
        cover = get_course_detail[7].tobytes()

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
            await context.bot.send_message(chat_id, text='مشکلی در ارسال کاور وجود داشت!\n\n' + text, parse_mode='html', reply_markup=InlineKeyboardMarkup(keyboard))
            return
    else:
        await query.edit_message_text('<b>• این دوره در دسترس نیست!</b>', parse_mode='html')


@check_is_admin
async def admin_remove_course(update, context):
    query = update.callback_query
    get_course_id = int(query.data.replace('admin_remove_course_', ''))
    if get_course_id not in confirm_remove_course:
        confirm_remove_course[get_course_id] = 1
        await query.answer('آیا از حذف این دوره مطمئن هستید؟\nبرای تایید دوباره گزینه حذف را بزنید.', show_alert=True)
        return

    is_delete_done = database_pool.execute('transaction', [{'query': f'DELETE FROM Course WHERE courseID = {get_course_id} RETURNING *', 'params': None}])
    if is_delete_done:
        text = 'دوره با موقفیت حذف شد!'
    else:
        text = 'در حذف دوره مشکلی وجود داشت'
    keyboard = [[InlineKeyboardButton('برگشت', callback_data='admin')]]
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='html')


@handle_telegram_conversetion_exceptions
async def admin_change(update, context):
    chat_id = update.effective_chat.id
    query = update.callback_query
    split_data = query.data.split('&')

    context.user_data['admin_change_course_id'] = split_data[2]
    context.user_data['admin_change_column'] = split_data[1]

    query.answer()
    text = "بسیار خب، اطلاعات جدید را بفرستید."
    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode='html')
    return EDIT_COURSE


@handle_telegram_conversetion_exceptions
async def update_course(update, context):
    chat_id = update.effective_chat.id

    course_id = context.user_data['admin_change_course_id']
    column = context.user_data['admin_change_column']
    file_id, media = None, None

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
    elif update.message.video:
        file_id = update.message.video.file_id
    elif update.message.voice:
        file_id = update.message.voice.file_id
    elif update.message.document:
        file_id = update.message.document.file_id
    else:
        media = update.message.text

    if file_id:
        file = await context.bot.get_file(file_id)
        media = await file.download_as_bytearray()

    is_udpate_done = database_pool.execute('transaction', [{'query': f'UPDATE Course SET {column} = %s WHERE courseID = {course_id} RETURNING *', 'params': (media,)}])

    if is_udpate_done:
        text = "تغییرات با موفقیت ذخیره شد!"
    else:
        text = 'مشکلی در آپدیت وجود داشت!'

    await context.bot.send_message(chat_id=chat_id, text=text)
    return ConversationHandler.END


update_course_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(admin_change, pattern=r'admin_change(.*)')],
    states={
        EDIT_COURSE: [MessageHandler(filters.ALL, update_course)],
    },
    fallbacks=[],
    per_chat=True,
    allow_reentry=True,
    conversation_timeout=1500,
)


@handle_telegram_conversetion_exceptions
async def admin_add_discount_code(update, context):
    chat_id = update.effective_chat.id
    query = update.callback_query
    query.answer()
    text = ("این کد تخفیف برای کدام کاربران است؟"
            "\nآیدی آن ها را با کاما جدا کرده و بفرستید"
            "\nاگر میخواهید برای همه فعال باشد 0 را بفرستید.")
    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode='html')
    return ADD_DISCOUNT_CODE_VALID_FOR_USER


@handle_telegram_conversetion_exceptions
async def get_discount_code_valid_for_user(update, context):
    chat_id = update.effective_chat.id
    get_users = update.message.text.replace(' ', '').split(',')
    context.user_data['discount_users'] = get_users
    text = ('این کد تا چه زمانی فعال است؟'
            '\nتاریخ را با این فرمت بفرستید:'
            '\nyy/mm/dd')
    await context.bot.send_message(chat_id=chat_id, text=text)
    return ADD_DISCOUNT_CODE_VALID_UNTIL


@handle_telegram_conversetion_exceptions
async def get_discount_code_valid_until(update, context):
    chat_id = update.effective_chat.id
    get_date = update.message.text
    context.user_data['discount_valid_until'] = get_date
    text = 'این کد چه مبلغی را کسر میکند؟ به تومان بفرستید.'
    await context.bot.send_message(chat_id=chat_id, text=text)
    return ADD_DISCOUNT_CODE_CREDIT


@handle_telegram_conversetion_exceptions
async def get_credit_and_generate(update, context):
    chat_id = update.effective_chat.id
    credit = int(update.message.text.replace(',', ''))
    until_date = context.user_data['discount_valid_until']
    allow_users = context.user_data['discount_users']
    generate_code = str(uuid.uuid4())[:8]

    if int(allow_users[0]) == 0 and len(allow_users) == 1:
        add_code = [(True, True, None, credit, until_date, generate_code)]
    else:
        add_code = [(True, False, int(user), credit, until_date, generate_code) for user in allow_users]

    values_template = ', '.join(['(%s, %s, %s, %s, %s, %s)'] * len(add_code))
    query = f'''
    INSERT INTO DiscountCode (is_active, available_for_all_user, for_userID, credit, valid_until, code) 
    VALUES {values_template}
    RETURNING discountID
    '''
    params = [item for sublist in add_code for item in sublist]
    try:
        result = database_pool.execute('transaction', [{'query': query, 'params': params}])
    except psycopg2.errors.DatetimeFieldOverflow:
        await context.bot.send_message(chat_id=chat_id, text='فرمت تایم درست نیست!', parse_mode='html')
        return ConversationHandler.END

    if result:
        text = ('کد تخفیف با موفقیت ساخته شد!'
                f'\n<code>{generate_code}</code>')
    else:
        text = 'مشکلی در ساخت کد تخفیف وجود داشت!'

    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode='html')
    return ConversationHandler.END


add_discount_code = ConversationHandler(
    entry_points=[CallbackQueryHandler(admin_add_discount_code, pattern=r'admin_add_discount_code')],
    states={
        ADD_DISCOUNT_CODE_VALID_FOR_USER: [MessageHandler(filters.TEXT, get_discount_code_valid_for_user)],
        ADD_DISCOUNT_CODE_VALID_UNTIL: [MessageHandler(filters.TEXT, get_discount_code_valid_until)],
        ADD_DISCOUNT_CODE_CREDIT: [MessageHandler(filters.TEXT, get_credit_and_generate)],
    },
    fallbacks=[],
    per_chat=True,
    allow_reentry=True,
    conversation_timeout=1500,
)
