import requests
from private import telegram_bot_url, ADMIN_CHAT_IDs


async def report_problem(func_name, error, side, extra_message=None):
    text = (f"🔴 BOT Report Problem [{side}]\n\n"
            f"\nFunc Name: {func_name}"
            f"\nError Type: {type(error).__name__}"
            f"\nError Reason:\n{error}"
            f"\nExtra Message:\n{extra_message}")

    requests.post(url=telegram_bot_url, data={'chat_id': ADMIN_CHAT_IDs[0], 'text': text})


async def report_problem_to_admin_witout_context(text, chat_id, error, detail=None):
    text = ("🔴 Report Problem in Bot\n\n"
            f"Something Went Wrong In {text} Section."
            f"\nUser ID: {chat_id}"
            f"\nError Type: {type(error).__name__}"
            f"\nError Reason:\n{error}")

    text += f"\nDetail:\n {detail}" if detail else ''
    requests.post(url=telegram_bot_url, data={'chat_id': ADMIN_CHAT_IDs[0], 'text': text})
    print(f'* REPORT TO ADMIN SUCCESS: ERR: {error}')


class WalletManage:
    def __init__(self, wallet_table, wallet_column, db_pool, user_id_identifier):
        self.db_pool = db_pool
        self.WALLET_TABALE = wallet_table
        self.WALLET_COLUMN = wallet_column
        self.USER_ID = user_id_identifier

    async def get_wallet_credit(self, user_id):
        get_credit = self.db_pool.execute('query', {'query': f'SELECT {self.WALLET_COLUMN} FROM {self.WALLET_TABALE} WHERE {self.USER_ID} = {user_id}'})
        return int(get_credit[0][0])

    async def get_all_wallet(self):
        get_credit = self.db_pool.execute('query', {'query': f'SELECT {self.WALLET_COLUMN} FROM {self.WALLET_TABALE}'})
        return get_credit


    async def add_to_wallet(self, user_id, credit):
        try:
            credit_all = int(await self.get_wallet_credit(user_id) + credit)
            get_credit = self.db_pool.execute('transaction', [{'query': f'UPDATE {self.WALLET_TABALE} SET {self.WALLET_COLUMN} = {credit_all} WHERE {self.USER_ID} = {user_id} RETURNING *',
                                                                'params': None}])
            return get_credit

        except Exception as e:
            await report_problem_to_admin_witout_context(chat_id=user_id, text='ADD TO WALLET [wallet script]', error=e)
            return None

    async def less_from_wallet(self, user_id, credit):
        try:
            credit_all = int(await self.get_wallet_credit(user_id) - credit)
            get_credit = self.db_pool.execute('transaction', [{'query': f'UPDATE {self.WALLET_TABALE} SET {self.WALLET_COLUMN} = {credit_all} WHERE {self.USER_ID} = {int(user_id)} RETURNING *', 'params': None}])
            return get_credit
        except Exception as e:
            await report_problem_to_admin_witout_context(chat_id=user_id, text='LESS FROM WALLET [wallet script]', error=e)
            return None

    def set_credit(self, user_id, credit):
        get_credit = self.db_pool.execute('transaction', [{'query': f'UPDATE {self.WALLET_TABALE} SET {self.WALLET_COLUMN} = {credit} WHERE {self.USER_ID} = {user_id} RETURNING *',
                                                            'params': None}])
        return get_credit

# a = WalletManage('User', 'wallet', 'chat_id')
# print(a.less_from_wallet(6450325872, 1))
# print(a.get_all_wallet())