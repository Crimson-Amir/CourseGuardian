from abc import ABC, abstractmethod
from datetime import datetime
import hashlib


class User(ABC):
    def __init__(self, db_client):
        self._db_client = db_client  # postgres request pool

    @abstractmethod
    async def execute(self, **kwargs):
        pass


class IsUserExist(User):
    async def execute(self, **kwargs):
        key = kwargs.get('key') or 'userID'
        column = kwargs.get('column') or '*'
        user_detail = self._db_client.execute('query', {'query': f'SELECT {column} FROM UserDetail WHERE {key} = %s', 'params': (kwargs.get('value'),)})
        if user_detail: return True, user_detail
        return False, ()


class AddRefralScore(User):
    async def execute(self, **kwargs):
        user_detail = kwargs.get('user_detail')
        user_id = user_detail[1]
        number_of_invitations = int(user_detail[8])
        user_detail = self._db_client.execute('transaction',
                                              [{'query': 'UPDATE UserDetail SET number_of_invitations = %s  WHERE userID = %s RETURNING *',
                                                'params': (number_of_invitations + 1, user_id)}])
        return user_detail


class RegisterUser(User):

    @staticmethod
    async def generate_referral_code(user_id) -> str:
        input_data = str(user_id) + str(datetime.now())
        return hashlib.md5(input_data.encode('utf-8')).hexdigest()

    async def check_referral(self, referral_link):
        if referral_link:
            get_user_detail = await IsUserExist(self._db_client).execute(key='referral_link', value=referral_link)

            if get_user_detail[0]:
                get_caller_chat_id = get_user_detail[1][0][1]
                await AddRefralScore(self._db_client).execute(user_detail=get_user_detail[1][0])
                return get_caller_chat_id


    async def execute(self, **kwargs):
        referral_link = kwargs.get('referral_link')
        user_detail = kwargs.get('user_detail')
        get_caller_chat_id = await self.check_referral(referral_link)
        generate_invite_link = await self.generate_referral_code(user_detail.id)

        create_user = self._db_client.execute('transaction',
                                              [{'query': 'INSERT INTO UserDetail (userID, first_name, last_name, entered_with_refral_link, referral_link) VALUES (%s,%s,%s,%s,%s) RETURNING *',
                                               'params': (
                                               user_detail.id, user_detail.first_name, user_detail.last_name,
                                               get_caller_chat_id, generate_invite_link)}])

        return create_user


class UserClient:
    def __init__(self, db_client):
        self._db_client = db_client

    async def execute(self, _calss, **kwargs):
        return await _calss(self._db_client).execute(**kwargs)
