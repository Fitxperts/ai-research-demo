"""Одноразовый логин юзербота → получить USERBOT_SESSION (StringSession).

Запусти в терминале (интерактивно, где есть доступ к номеру телефона):

    python scripts/userbot_login.py

Понадобятся API_ID и API_HASH с https://my.telegram.org → API development tools.
Введёшь номер телефона аккаунта-«читателя» и код из Telegram. В конце скрипт
напечатает строку сессии — скопируй её в .env как USERBOT_SESSION.

⚠️ Используй ОТДЕЛЬНЫЙ номер (не личный): юзерботы формально против ToS Telegram.
Строку сессии храни как секрет — это полный доступ к аккаунту.
"""
from telethon import TelegramClient
from telethon.sessions import StringSession


def main() -> None:
    api_id = int(input("API_ID: ").strip())
    api_hash = input("API_HASH: ").strip()
    with TelegramClient(StringSession(), api_id, api_hash) as client:
        session = client.session.save()
        print("\n=== СКОПИРУЙ В .env ===")
        print(f"USERBOT_SESSION={session}")
        print("======================")


if __name__ == "__main__":
    main()
