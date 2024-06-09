from utilities import database_pool, handle_telegram_conversetion_exceptions
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import psycopg2
from private import ADMIN_CHAT_IDs
from telegram.ext import ConversationHandler, MessageHandler, filters, CallbackQueryHandler

admin_page_keyboard = [[InlineKeyboardButton('اضافه کردن دوره', callback_data='admin_add_course_page')]]

(GET_TITLE, GET_DESCRIPTION, GET_COVER, GET_DISCOUNT_PERCENT_PER_INVITE, GET_DISCOUNT, GET_NUMBER_OF_REFERRAL_TO_BE_FREE,
GET_PRICE, GET_STATUS, GET_CONTENT, PRIVATE_CHANNEL_CHAT_ID) = range(10)

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
        [InlineKeyboardButton('فایل تصویری', callback_data='admin_add_course_image')],
        [InlineKeyboardButton('فایل ویدیویی', callback_data='admin_add_course_video')],
        [InlineKeyboardButton('فایل صوتی', callback_data='admin_add_course_voice')],
        [InlineKeyboardButton('لینک کانال', callback_data='admin_add_course_chennel_link')]]
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
    elif course_content_type == 'image':
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
