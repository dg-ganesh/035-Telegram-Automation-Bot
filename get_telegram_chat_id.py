
import getpass
import json
import urllib.error
import urllib.parse
import urllib.request


API_BASE = "https://api.telegram.org/bot"


def telegram_request(token, method):
    url = f"{API_BASE}{token}/{method}"
    request = urllib.request.Request(url)

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        try:
            details = json.loads(details).get("description", details)
        except json.JSONDecodeError:
            pass
        raise RuntimeError(
            f"Telegram API error ({error.code}): {details}"
        ) from None


def main():
    print("Telegram Chat ID Finder")
    print("-----------------------")
    token = getpass.getpass("Enter your bot token (input hidden): ").strip()

    if not token:
        print("No token entered.")
        return

    try:
        # Confirm that the token identifies your bot.
        bot_result = telegram_request(token, "getMe")
        if not bot_result.get("ok"):
            print("Telegram could not verify the bot token.")
            return

        bot = bot_result["result"]
        print(f"\nConnected to bot: @{bot.get('username', 'unknown')}")

        # Check whether a webhook prevents getUpdates from working.
        webhook_result = telegram_request(token, "getWebhookInfo")
        webhook = webhook_result.get("result", {})
        webhook_url = webhook.get("url", "")

        if webhook_url:
            print("\nA webhook is configured.")
            print("getUpdates cannot be used while this webhook is active.")
            print("No webhook settings have been changed.")
            return

        # Read pending updates without acknowledging or consuming them.
        updates_result = telegram_request(token, "getUpdates")

        if not updates_result.get("ok"):
            print("Telegram did not return updates.")
            return

        updates = updates_result.get("result", [])
        found = False

        for update in updates:
            message = (
                update.get("message")
                or update.get("edited_message")
                or update.get("channel_post")
                or update.get("edited_channel_post")
            )

            if not message:
                continue

            chat = message.get("chat", {})
            chat_id = chat.get("id")
            chat_type = chat.get("type", "unknown")
            username = chat.get("username")
            first_name = chat.get("first_name")
            title = chat.get("title")
            text = message.get("text", "")

            print("\nIncoming message found:")
            print(f"  Chat ID:   {chat_id}")
            print(f"  Chat type: {chat_type}")
            print(f"  Name:      {title or first_name or 'Not provided'}")
            print(f"  Username:  @{username}" if username else
                  "  Username:  Not provided")
            print(f"  Message:   {text[:100]}")
            found = True

        if not found:
            print("\nNo pending messages were found.")
            print("Send a NEW message to your bot from ID-B,")
            print("then run this script again.")
            print("If updates are being consumed elsewhere,")
            print("we will need to investigate that separately.")

    except (RuntimeError, urllib.error.URLError, TimeoutError) as error:
        print(f"\nCould not retrieve the chat ID: {error}")

    finally:
        # Do not print or save the bot token.
        token = None


if __name__ == "__main__":
    main()
