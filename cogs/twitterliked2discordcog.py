from discord.ext import tasks, commands
from discord import app_commands
from logging import getLogger
from typing import Literal
from .modules.liked_twitter import LikedTwitter
from .modules import settings

import discord

LOG = getLogger('twitterliked2discordbot')

# コグとして用いるクラスを定義。
class TwitterLiked2DiscordCog(commands.Cog):
    guilds = settings.ENABLE_SLASH_COMMAND_GUILD_ID
    SHOW_ME = '自分のみ'

    # TwitterLiked2DiscordCogクラスのコンストラクタ。Botを受取り、インスタンス変数として保持。
    def __init__(self, bot):
        self.bot = bot
        self.likedTwitter = LikedTwitter(bot)
        self.info = None

    # 読み込まれた時の処理
    @commands.Cog.listener()
    async def on_ready(self):
        await self.likedTwitter.prepare()  # dbを作成
        self.info = await self.bot.application_info()
        LOG.info('SQlite準備完了')
        LOG.debug(self.bot.guilds)
        self.printer.start()

    def cog_unload(self):
        self.printer.cancel()

    @tasks.loop(hours=24.0)
    async def printer(self):
        LOG.info('printer start')
        count = 0
        for row in self.likedTwitter.liked_twitter_rows:
            # 取得
            send_list, id = await self.likedTwitter.liked_to_recent_list(row[1],row[2],row[3]) # bearer_token twitter_id liked_twitter_id
            # 送信
            if send_list and len(send_list) > 0:
                await self.likedTwitter.send_discord(send_list, row[4], row[5]) # guild_id channel_id
                self.likedTwitter.update_liked_twitter_id(row[0], row[2], id) # discord_id guild_id
                count = count + 1
        LOG.info(f'printer end: {count}')

    @app_commands.command(
        name='set-bearer-token',
        description='bearer_tokenをセット(必須)')
    @app_commands.describe(
        bearer_token='TwitterのDeveloper Portalでbearer_tokenを取得しておき、こちらに入力してください')
    @app_commands.describe(
        reply_is_hidden='Botの実行結果を全員に見せるどうか(他の人にもコマンドを使わせたい場合、全員に見せる方がオススメです))')
    async def _set_bearer_token(self,
                        interaction: discord.Interaction,
                        bearer_token: str,
                        reply_is_hidden: Literal['自分のみ', '全員に見せる'] = SHOW_ME):
        LOG.info(f'bearer_tokenをセット(discord_id: {interaction.user.id})')
        hidden = True if reply_is_hidden == self.SHOW_ME else False
        self.check_printer_is_running()
        self.likedTwitter.set_bearer_token(interaction.user.id, bearer_token)
        await interaction.response.send_message('bearer_tokenを設定しました', ephemeral=hidden)

    @app_commands.command(
        name='toggle-bearer-token',
        description='bearer_tokenの有効/無効を切り替え')
    @app_commands.describe(
        reply_is_hidden='Botの実行結果を全員に見せるどうか(他の人にもコマンドを使わせたい場合、全員に見せる方がオススメです))')
    async def _toggle_bearer_token(self,
                        interaction: discord.Interaction,
                        reply_is_hidden: Literal['自分のみ', '全員に見せる'] = SHOW_ME):
        LOG.info(f'bearer_tokenの有効/無効を切り替え(discord_id: {interaction.user.id})')
        hidden = True if reply_is_hidden == self.SHOW_ME else False
        await interaction.response.defer(ephemeral = hidden)
        self.check_printer_is_running()
        result = self.likedTwitter.toggle_bearer_token(interaction.user.id)
        if result is None:
            await interaction.followup.send('まだ有効なbearer_tokenが登録されていません', ephemeral=hidden)
            return
        await interaction.followup.send(f'bearer_tokenを{result}に設定しました', ephemeral=hidden)

    @app_commands.command(
        name='add-liked-user-from-name',
        description='TwitterのLikedを取得したいユーザを追加(usernameを入力(@の後の文字列))')
    @app_commands.describe(
        twitter_user_name='username(@の後の文字列)を指定')
    @app_commands.describe(
        reply_is_hidden='Botの実行結果を全員に見せるどうか(他の人にもコマンドを使わせたい場合、全員に見せる方がオススメです))')
    async def _addLikedUserFromName(self,
                        interaction: discord.Interaction,
                        twitter_user_name: str,
                        reply_is_hidden: Literal['自分のみ', '全員に見せる'] = SHOW_ME):
        hidden = True if reply_is_hidden == self.SHOW_ME else False
        self.check_printer_is_running()

        # チェック
        token = self.likedTwitter.bearer_token_from_discord_id(interaction.user.id)
        if not token:
            await interaction.response.send_message('あらかじめ、`/set-bearer-token`でトークンを設定してください。Twitter開発者ポータルで取得できます', ephemeral=True)
            return
        await interaction.response.defer(ephemeral = hidden)

        # Twitter User NameからTwitter Idを変換(無理ならエラー)
        twitter_user_id = await self.likedTwitter.user_id_from_user_name(token, twitter_user_name)
        LOG.info(f'LikedしたいTwitterユーザを追加(username指定): {twitter_user_name}')
        if not twitter_user_id:
            await interaction.followup.send('ユーザIDの取得に失敗しました。見直しをお願いします。', ephemeral=hidden)
            return

        # Likedしたいユーザを追加(discordId,TwitterId,TwitterName,GuildId,ChannelId)
        res = await self.likedTwitter.liked_tweets_from_user_id(token, interaction.user.id, twitter_user_id, twitter_user_name,interaction.guild.id, interaction.channel.id)
        if res:
            await interaction.followup.send('Liked監視対象のTwitterIDを設定しました', ephemeral=hidden)
        else:
            await interaction.followup.send('何も取得できませんでした。対象が誤っているか、トークンが無効です。', ephemeral=hidden)

    @app_commands.command(
        name='add-liked-user-from-id',
        description='TwitterのLikedを取得したいユーザを追加(idを入力(ユーザーIDと呼ばれるもの。開発者的なツールが必要かも))')
    @app_commands.describe(
        twitter_user_id='idを指定(数字必須)')
    @app_commands.describe(
        reply_is_hidden='Botの実行結果を全員に見せるどうか(他の人にもコマンドを使わせたい場合、全員に見せる方がオススメです))')
    async def _addLikedUserFromId(self,
                        interaction: discord.Interaction,
                        twitter_user_id: str,
                        reply_is_hidden: Literal['自分のみ', '全員に見せる'] = SHOW_ME):
        hidden = True if reply_is_hidden == self.SHOW_ME else False
        self.check_printer_is_running()
        # チェック
        if not twitter_user_id.isdigit():
            await interaction.response.send_message('twitter_user_idは数字である必要があります', ephemeral=True)
            return
        token = self.likedTwitter.bearer_token_from_discord_id(interaction.user.id)
        if not token:
            await interaction.response.send_message('あらかじめ、`/set-bearer-token`でトークンを設定してください。Twitter開発者ポータルで取得できます', ephemeral=True)
            return
        await interaction.response.defer(ephemeral = hidden)

        # Twitter User NameからTwitter Idを変換(無理ならエラー)
        LOG.info(f'LikedしたいTwitterユーザを追加(id指定): {twitter_user_id}')
        twitter_user_name = await self.likedTwitter.user_name_from_user_id(token, twitter_user_id)
        if not twitter_user_name:
            await interaction.followup.send('ユーザ名の取得に失敗しました。見直しをお願いします。', ephemeral=hidden)
            return

        # Likedしたいユーザを追加
        res = await self.likedTwitter.liked_tweets_from_user_id(token, interaction.user.id, twitter_user_id, twitter_user_name,interaction.guild.id, interaction.channel.id)
        if res:
            await interaction.followup.send('Liked監視対象のTwitterIDを設定しました', ephemeral=hidden)
        else:
            await interaction.followup.send('何も取得できませんでした。対象が誤っているか、トークンが無効です。', ephemeral=hidden)

    # @app_commands.command(
    #     name='remind-list',
    #     description='remindを確認する')
    # @app_commands.describe(
    #     status='リマインドリストで表示させるステータス')
    # @app_commands.describe(
    #     filter='リマインドリストを検索')
    # @app_commands.describe(
    #     reply_is_hidden='Botの実行結果を全員に見せるどうか(他の人にもコマンドを使わせたい場合、全員に見せる方がオススメです))')
    # async def remind_list(self,
    #                     interaction: discord.Interaction,
    #                     status: Literal['実行予定のリマインドリスト(デフォルト)', 'キャンセルしたリマインドリスト', 'スキップしたリマインドリスト', '終了したリマインドリスト', 'エラーになったリマインドリスト'] = '実行予定のリマインドリスト(デフォルト)',
    #                     filter: str = None,
    #                     reply_is_hidden: Literal['自分のみ', '全員に見せる'] = SHOW_ME):
    #     LOG.info('remindをlistするぜ！')
    #     hidden = True if reply_is_hidden == self.SHOW_ME else False
    #     await interaction.response.defer(ephemeral = hidden)
    #     command_status = self.get_command_status(status)
    #     self.check_printer_is_running()

    #     rows = self.remind.list(interaction, command_status, filter)
    #     await interaction.followup.send(rows, ephemeral = hidden)

    @app_commands.command(
        name='twitter-task-check',
        description='Taskを確認する(このBotが発動しない場合に実行してください)')
    @app_commands.describe(
        reply_is_hidden='Botの実行結果を全員に見せるどうか(他の人にもコマンドを使わせたい場合、全員に見せる方がオススメです))')
    async def _twitter_task_check(self,
                                interaction: discord.Interaction,
                                reply_is_hidden: Literal['自分のみ', '全員に見せる'] = SHOW_ME):
        LOG.info('liked twitterのTaskを確認するぜ！')
        hidden = True if reply_is_hidden == self.SHOW_ME else False
        await interaction.response.defer(ephemeral = hidden)
        msg = 'Taskは問題なく起動しています。'
        self.check_printer_is_running()
        await interaction.followup.send(msg, ephemeral = hidden)

    def check_printer_is_running(self):
        if not self.printer.is_running():
            msg = 'Taskが停止していたので再起動します。'
            LOG.info(msg)
            self.printer.start()

    async def cog_app_command_error(self, interaction, error):
        '''
        slash_commandでエラーが発生した場合の動く処理
        '''
        LOG.error(error)
        if isinstance(error, app_commands.CheckFailure):
            if interaction.command.name == 'remind-list-all':
                await interaction.response.send_message(f'エラーが発生しました(DM(ダイレクトメッセージ)でのみ実行できます)', ephemeral=True)
            else:
                await interaction.response.send_message(f'エラーが発生しました(コマンドが実行できません)', ephemeral=True)
        elif isinstance(error, discord.ext.commands.PrivateMessageOnly):
            await interaction.response.send_message(f'エラーが発生しました(DM(ダイレクトメッセージ)でのみ実行できます)', ephemeral=True)
        elif isinstance(error, app_commands.NoPrivateMessage):
            await interaction.response.send_message(f'エラーが発生しました(ギルドでのみ実行できます(DMやグループチャットでは実行できません))', ephemeral=True)
        elif isinstance(error, discord.ext.commands.NotOwner):
            await interaction.response.send_message(f'エラーが発生しました(Botのオーナーのみ実行できます)', ephemeral=True)
        elif isinstance(error, app_commands.MissingPermissions):
            if error.missing_perms[0] == 'administrator':
                await interaction.response.send_message(f'エラーが発生しました(ギルドの管理者のみ実行できます)', ephemeral=True)
            else:
                await interaction.response.send_message(f'エラーが発生しました(権限が足りません)', ephemeral=True)
        elif isinstance(error, discord.errors.Forbidden):
            await interaction.response.send_message(f'エラーが発生しました(権限が足りません(おそらくBotが表示/編集できない))', ephemeral=True)
        else:
            await interaction.response.send_message(f'エラーが発生しました({error})', ephemeral=True)

# Bot本体側からコグを読み込む際に呼び出される関数。
async def setup(bot):
    LOG.info('TwitterLiked2DiscordCogを読み込む！')
    await bot.add_cog(TwitterLiked2DiscordCog(bot))  # TwitterLiked2DiscordCogにBotを渡してインスタンス化し、Botにコグとして登録する。
