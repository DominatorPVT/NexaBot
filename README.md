# 🤖 NexaBot

A Telegram bot with AI chatbot, UNO game, and MongoDB storage.

## Setup

1. Open `config.py` and fill these:

```python
BOT_TOKEN = "your bot token from @BotFather"
BOT_NAME  = "NexaBot"
OWNER_ID  = 123456789
ADMIN_IDS = [123456789]
MONGO_URI = "mongodb+srv://user:pass@cluster.mongodb.net/nexabot"
UNO_STICKER_PACK_URL = "https://t.me/addstickers/classic_colorblind"
```

### Get Owner ID
Message [@userinfobot](https://t.me/userinfobot) on Telegram — it replies with your user ID.

### Get MongoDB URI
1. Sign up free at [MongoDB Atlas](https://cloud.mongodb.com)
2. Create a free cluster
3. Database Access → create a user
4. Network Access → allow `0.0.0.0/0`
5. Connect → Drivers → copy the connection string

### Change UNO stickers
Replace `UNO_STICKER_PACK_URL` with any sticker pack link (format: `https://t.me/addstickers/pack_name`).

### Edit AI personality
`CUSTOM_PROMPT` in `config.py` controls how the bot talks. Edit it directly.

## Run Locally

```bash
pip install -r requirements.txt
python bot.py
```

## Host on a VPS (24/7)

```bash
ssh root@your_server_ip
apt update && apt install python3 python3-pip python3-venv git -y
git clone <your-repo-url> nexabot && cd nexabot
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
nano config.py   # fill in your values, save with CTRL+O then CTRL+X
```

Create a systemd service so it runs forever and auto-restarts:

```bash
sudo nano /etc/systemd/system/nexabot.service
```

Paste:
```ini
[Unit]
Description=NexaBot
After=network.target

[Service]
WorkingDirectory=/root/nexabot
ExecStart=/root/nexabot/venv/bin/python3 /root/nexabot/bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Start it:
```bash
sudo systemctl daemon-reload
sudo systemctl enable nexabot
sudo systemctl start nexabot
```

Useful commands:
```bash
sudo systemctl restart nexabot   # restart
sudo systemctl stop nexabot      # stop
journalctl -u nexabot -f         # view logs
```

## Host on GitHub Actions (manual, runs while job is active)

1. Push this repo to GitHub.
2. Go to **Settings → Secrets and variables → Actions** and add:
   - `BOT_TOKEN`
   - `MONGO_URI`
   - `OWNER_ID`
3. Go to the **Actions** tab → select **Run NexaBot** → click **Run workflow**.
4. Bot stays online until the job times out (max 6 hours), then click **Run workflow** again to bring it back.

## Host on GitLab CI (manual, runs while job is active)

1. Push this repo to GitLab.
2. Go to **Settings → CI/CD → Variables** and add:
   - `BOT_TOKEN`
   - `MONGO_URI`
   - `OWNER_ID`
3. Go to **Build → Pipelines** → **Run pipeline**.
4. Click the ▶️ play button next to the `run-bot` job to start it.
5. When the job times out, repeat to bring the bot back online.

## Commands

| Command | What it does |
|---|---|
| `/start` | Welcome message with menu buttons |
| `/help` | List all commands |
| `/ping` | Check response time |
| `/id` | Get user ID, chat ID, message ID |
| `/chatbot` | Enable/disable AI chatbot (group admins) |
| `/stats` | Bot stats (owner/admins) |
| `/uno` | Start a UNO game |
| `/broadcast <text>` | Send message to all chats (owner/admins) |
| `/broadcast -pin <text>` | Same, but pins it too |

## How UNO works

1. `/uno` opens a lobby.
2. Players tap **Join Game**.
3. Host taps **Start Game**.
4. Bot deals 7 cards each with an animation.
5. On your turn, tap **Play your cards** to see your hand privately and play a card, or draw one.
6. First to finish their hand wins — bot sends a sticker and announces winner/loser.
