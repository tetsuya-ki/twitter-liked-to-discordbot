# このBotについて

- IFTTTでTwitter連携が終了してしまったため急遽作成したBotです
  - TwitterでいいねしたものをDiscordに転送するように設定していたため
  - Bearer Tokenが必要なので使いづらいと思います(自分用です)

## コマンド

### /set-bearer-token

- TwitterのAPIを実行するのに必要なBearer Token(以降トークン)を設定するコマンドです
- 大抵のコマンドはあらかじめ、このコマンドでトークンを設定しておく必要があります
- Twitterの開発者ポータルで取得可能です

### /toggle-bearer-token

- 自分のBearer Tokenの有効/無効を切り替えるコマンドです([v0.2.0](https://github.com/tetsuya-ki/twitter-liked-to-discordbot/releases/tag/v0.2.0)で追加)
- トークン無効時は、そのDiscordIDで登録されているTwitterのLikeを見ません

### /add-liked-user-from-name

- likedを監視する対象のユーザーを設定するコマンドです
  - `@xxxxx`でメンションするときのxxxxx部分を使って指定します

### /add-liked-user-from-id

- 前述のコマンドのidバージョンです(大抵の人はid知らないので使いづらいかもしれません)

### /remove-liked-user-from-name

- likedを監視する対象のユーザーを削除するコマンドです([v0.2.0](https://github.com/tetsuya-ki/twitter-liked-to-discordbot/releases/tag/v0.2.0)で追加)
  - `@xxxxx`でメンションするときのxxxxx部分を使って指定します

### /remove-liked-user-from-id

- likedを監視する対象のユーザーを削除するコマンドです([v0.2.0](https://github.com/tetsuya-ki/twitter-liked-to-discordbot/releases/tag/v0.2.0)で追加)

### /twitter-task-check

- このBotが定期的に確認する状態かをチェックするコマンドです
  - なお、何かコマンドを実行した際にも自動でチェックされます

## 今後実装予定のコマンド

### 考えてない

## 環境変数

- `DISCORD_TOKEN`(必須)
  - DiscordのBotを動かすためのトークンです
- `APPLICATION_ID`(必須)
  - DiscordのBotがスラッシュコマンドを使うために必要なIDです
- `LOG_LEVEL`(オプション: デフォルトはINFO)
  - ログのレベルです(INFO, DEBUGなど)
- `KEEP_DECRYPTED_FILE`(オプション: デフォルトはFALSE(暗号化前ファイルは削除))
  - このBotでは重要な情報は暗号化されます。暗号化前のファイルを残すかどうかの設定です
- `ENABLE_SLASH_COMMAND_GUILD_ID`(オプション: デフォルトは設定なし)
  - 試験などで一部ギルドのみスラッシュコマンドを使わせる場合に使用します

## 動かし方

### 前提条件

- Poetryがインストールされていること
  - インストールされていない場合は[公式の手順](https://python-poetry.org/docs/#installing-with-the-official-installer)を参考にしてください
  - なお、<https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py>が使われている手順は古いです

### 動かし方A(シェルを使う)

```sh
git clone https://github.com/tetsuya-ki/twitter-liked-to-discordbot.git
cd twitter-liked-to-discordbot
chmod 755 start.sh
./start.sh
```

### 動かし方B

```sh
git clone https://github.com/tetsuya-ki/twitter-liked-to-discordbot.git
cd twitter-liked-to-discordbot
poetry install
poetry run python twitter-liked-to-discordbot.py
```
