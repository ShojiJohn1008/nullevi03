# ナルエビちゃん三世

AI秘書っす。

## 使い方

- Claude に月200ドルとか課金する

- Telegramを頑張って入れる。Botfatherとか。

- Claude Code Channelsを頑張って設定する。

- boot.sh で起動

- あとは、死ぬほど会話とかする

- 終わり

## 朝のブリーフィング

毎朝、日付・天気・TODO をまとめて Telegram に送ってくれるやつ。

```sh
TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... ./briefing.sh
```

毎朝 7 時に送らせるなら crontab に登録する (`crontab -e`):

```
0 7 * * * cd /path/to/nullevi03 && TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... BRIEFING_LOCATION=Tokyo ./briefing.sh
```

- 天気の地域は `BRIEFING_LOCATION` で変えられる (デフォルト Tokyo)
- ブリーフィングの中身は `prompts/briefing.md` を編集して調整する
- TODO は `memory/todo.md` に書いておくと読み上げてくれる。Telegram で「TODO に〇〇追加して」と頼んでもいい

## トラブルシューティング

- AIに聞け！俺には聞くな！！

## ライセンス

ナルエビちゃんライセンスに従うものとする。（まだない）

## 免責事項

家が燃えたとか、なんか起きても全て責任は負わないです。

