import aiohttp, datetime, discord, sqlite3, os, locale
from os.path import join, dirname
from datetime import timedelta, timezone
from logging import getLogger
from enum import Enum
from .aes_angou import Aes_angou
from . import settings

LOG = getLogger('twitterliked2discordbot')

class LikedTwitter:
    TWITTER_V2='https://api.twitter.com/2/'
    DATABASE = 'liked_twitter.db'
    FILE_PATH = join(dirname(__file__), 'files' + os.sep + DATABASE)
    STATUS_VALID = 'VALID'
    STATUS_INVALID = 'INVALID'
    JST = timezone(timedelta(hours=9), 'JST')

    def __init__(self, bot):
        self.bot = bot
        self.liked_twitter_rows = None
        self.aes = Aes_angou(settings.DISCORD_TOKEN)

    async def prepare(self):
        '''
        sqlite3のdbを準備する
        '''
        if not os.path.exists(self.aes.ENC_FILE_PATH):
            conn = sqlite3.connect(self.FILE_PATH)
            with conn:
                cur = conn.cursor()

                create_user_table_sql = '''
                                    create table if not exists user (
                                        discord_id text primary key,
                                        bearer_token text,
                                        status text,
                                        created_at datetime,
                                        updated_at datetime
                                    )
                                    '''
                cur.execute(create_user_table_sql)

                create_liked_user_table_sql = '''
                                    create table if not exists liked_user (
                                        discord_id text,
                                        twitter_id text,
                                        twitter_name text,
                                        liked_twitter_id text,
                                        guild_id text,
                                        channel_id text,
                                        created_at datetime,
                                        primary key(discord_id,twitter_id)
                                    )
                                    '''
                cur.execute(create_liked_user_table_sql)

        else:
            self.decode()
        self.read()
        self.encode()
        LOG.info('準備完了')

    def decode(self):
        if os.path.exists(self.aes.ENC_FILE_PATH):
            self.aes.decode()
            os.remove(self.aes.ENC_FILE_PATH)

    def encode(self):
        if os.path.exists(self.aes.DEC_FILE_PATH):
            self.aes.encode()
            if settings.KEEP_DECRYPTED_FILE:
                os.remove(self.aes.DEC_FILE_PATH)

    def read(self, num = 500):
        # readはdecodeしない
        conn = sqlite3.connect(self.FILE_PATH)
        with conn:
            cur = conn.cursor()
            select_sql = f'''
                            select user.discord_id, user.bearer_token, liked_user.twitter_id, liked_user.liked_twitter_id, liked_user.guild_id, liked_user.channel_id
                            from user
                            inner join liked_user
                                on user.discord_id = liked_user.discord_id
                            where user.status = '{self.STATUS_VALID}' order by user.created_at
                        '''
            LOG.debug(select_sql)
            cur.execute(select_sql)
            self.liked_twitter_rows = cur.fetchmany(num)
            LOG.info(f'＊＊＊＊＊＊読み込みが完了しました({len(self.liked_twitter_rows)}件)＊＊＊＊＊＊')
            LOG.debug(self.liked_twitter_rows)

    def set_bearer_token(self, discord_id, bearer_token):
        self.decode()
        conn = sqlite3.connect(self.FILE_PATH)
        with conn:
            cur = conn.cursor()
            now = datetime.datetime.now(self.JST)
            upsert_sql = f'''
                            insert into user values
                                ('{discord_id}', '{bearer_token}', '{self.STATUS_VALID}', '{now}', '{now}')
                            on conflict(discord_id)
                                do update
                                set bearer_token = '{bearer_token}',
                                status = '{self.STATUS_VALID}',
                                updated_at = '{now}';
                        '''
            LOG.debug(upsert_sql)
            cur.execute(upsert_sql)
        self.read()
        self.encode()

    def _set_liked_user(self, discord_id, twitter_user_id, twitter_user_name, guild_id, channel_id):
        self.decode()
        conn = sqlite3.connect(self.FILE_PATH)
        with conn:
            cur = conn.cursor()
            now = datetime.datetime.now(self.JST)
            upsert_sql = f'''
                            insert into liked_user values
                                ('{discord_id}', '{twitter_user_id}', '{twitter_user_name}', '', '{guild_id}', '{channel_id}', '{now}')
                            on conflict(discord_id, twitter_id)
                                do update
                                set twitter_name = '{twitter_user_name}',
                                guild_id = '{guild_id}',
                                channel_id = '{channel_id}'
                        '''
            LOG.debug(upsert_sql)
            cur.execute(upsert_sql)
        self.read()
        self.encode()

    def bearer_token_from_discord_id(self, discord_id):
        self.decode()
        token = ''
        conn = sqlite3.connect(self.FILE_PATH)
        with conn:
            cur = conn.cursor()
            select_sql = f'''
                            select bearer_token from user
                            where status = '{self.STATUS_VALID}' and discord_id = '{discord_id}'
                        '''
            LOG.debug(select_sql)
            cur.execute(select_sql)
            result = cur.fetchmany(1)
            if len(result) > 0:
                token = result[0][0]
        self.encode()
        return token

    def update_liked_twitter_id(self,discord_id, twitter_id, liked_twitter_id):
        self.decode()
        conn = sqlite3.connect(self.FILE_PATH)
        with conn:
            cur = conn.cursor()
            update_sql = f'''
                            update liked_user
                            set liked_twitter_id = '{liked_twitter_id}'
                            where discord_id = '{discord_id}'
                                and twitter_id = '{twitter_id}'
                        '''
            LOG.debug(update_sql)
            cur.execute(update_sql)
        self.read()
        self.encode()

    async def user_id_from_user_name(self, token, name):
        path = f'users/by/username/{name}'
        res = await self.get(authorization=token, path=path)
        LOG.debug(res)
        if isinstance(res, dict):
            data = res.get('data')
            if isinstance(data, dict):
                return data.get('id')

    async def user_name_from_user_id(self, token, id):
        path = f'users/{id}'
        res = await self.get(authorization=token, path=path)
        LOG.debug(res)
        if isinstance(res, dict):
            data = res.get('data')
            if isinstance(data, dict):
                return data.get('username')

    async def liked_tweets_from_user_id(self, token, discord_id, twitter_user_id, twitter_user_name, guild_id, channel_id):
        path = f'users/{twitter_user_id}/liked_tweets'
        get_param = '?max_results=5'
        res = await self.get(authorization=token, path=path, get_param=get_param)
        if res:
            self._set_liked_user(discord_id, twitter_user_id, twitter_user_name, guild_id, channel_id)
            LOG.debug(res)
        else:
            LOG.info('何も取得されませんでした。')
        return res

    # discord_id bearer_token twitter_id liked_twitter_id guild_id channel_id
    async def liked_to_recent_list(self, bearer_token:str,twitter_id:str,liked_twitter_id:str):
        path = f'users/{twitter_id}/liked_tweets'
        get_param = '?user.fields=created_at&tweet.fields=created_at,entities&max_results=10'
        res = await self.get(authorization=bearer_token, path=path, get_param=get_param)
        recent_list = list()
        id = 0
        if not res or res['meta']['result_count'] == 0:
            return recent_list, None
        else:
            data = res['data']
            id = data[0]['id']
            for current in data:
                if current['id'] == liked_twitter_id:
                    break
                else:
                    message = str(current['text'])
                    if current.get('entities') and current.get('entities').get('urls'):
                        # urlsにあるURLで書き換え(展開)していく(expanded_urlがtwitter.comだったら/photo/1を消す)
                        for url in current['entities']['urls']:
                            replace_str = str(url['expanded_url'])
                            if str(url['expanded_url']).startswith('https://twitter.com/'):
                                replace_str = str(url['expanded_url']).replace('/photo/1', '')
                            message = message.replace(url['url'], replace_str)
                    message += '\n投稿日時: ' + self.iso8601_to_jst_text(str(current['created_at']))
                    recent_list.append(message)
        return recent_list, id

    async def send_discord(self, list, guild_id, channel_id):
        try:
            guild = await self.bot.fetch_guild(guild_id)
            channel = guild.get_channel_or_thread(channel_id)
            if channel is None:
                channel = await guild.fetch_channel(channel_id)
            list.reverse()
            for item in list:
                await channel.send(item)
        except:
            LOG.error('エラーが発生')

    async def get(self, authorization:str, path:str='', get_param:str=''):

        response = None
        url = self.TWITTER_V2 + path
        authorization_token = f'Bearer {authorization}'
        headers = {
            "Authorization": authorization_token
            , "Accept": "*/*"
            , "Cache-Control": "no-cache"
            , "Host": "api.twitter.com"
            , "Accept-Encoding": "gzip, deflate, br"
            , "Connection": "keep-alive"
            }
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url + get_param) as r:
                if r.status == 200:
                    response = await r.json()
                    return response
                else:
                    self.r_err = 'リクエストに失敗しました。'
                    LOG.warn(self.r_err)
                    LOG.warn(r)
                    return

    def iso8601_to_jst_text(self, iso8601:str):
        dt_utc = datetime.datetime.fromisoformat(iso8601.replace('Z', '+00:00')) # python3.11から不要だが...
        locale.setlocale(locale.LC_TIME, 'ja_JP.UTF-8')
        return dt_utc.astimezone(self.JST).strftime('%Y/%m/%d(%a) %H:%M:%S')