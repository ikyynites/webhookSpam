from os import name as os_name, system as exec_command
from os.path import exists, isfile, splitext
from time import sleep
from json import dumps as to_json
from requests import get, post, delete, patch
from requests.structures import CaseInsensitiveDict
from tqdm import tqdm
from base64 import b64encode

# fine tune to your liking. if you continuously get rate limited, i suggest increasing. if it is too slow
# after one rate limit, i suggest decreasing.
EXTRA_DELAY_PER_PREV_RATE_LIMIT = 1.0
UNIVERSAL_DELAY_PER_PREV_RATE_LIMIT = EXTRA_DELAY_PER_PREV_RATE_LIMIT / 5

HEADERS = CaseInsensitiveDict()
HEADERS["Content-Type"] = "application/json"


def send(send_url, send_payload):
    response = post(url=send_url, headers=HEADERS, data=send_payload)
    return response


def update(patch_url, patch_payload):
    headers = CaseInsensitiveDict()
    headers["Content-Type"] = "application/json"

    response = patch(url=patch_url, headers=HEADERS, data=patch_payload)
    return response


def make_payload(payload_content):
    return to_json({"content": payload_content, "embeds": None, "attachments": [], "tts": text_to_speech})


def update_payload(update_name="", update_avatar_path=""):
    payload = {}

    if update_name != "":
        payload["name"] = update_name
    if update_avatar_path != "":

        if exists(update_avatar_path) and isfile(update_avatar_path) and \
                splitext(update_avatar_path)[1] in [".png", ".jpg", ".jpeg"]:
            with open(update_avatar_path, "rb") as avatar_filestream:
                avatar_base64 = b64encode(avatar_filestream.read())

            extension = ""
            if splitext(update_avatar_path)[1] == ".png":
                extension = "png"
            elif splitext(update_avatar_path)[1] in [".jpg", ".jpeg"]:
                extension = "jpeg"

            payload["avatar"] = f"data:image/{extension};base64,{avatar_base64.decode('utf-8')}"

    return to_json(payload)


def handle_rate_limit(handle_type, response, previous_rate_limits):
    print(f" {handle_type} was rate-limited, sleeping for " +
          f"{response.json().get('retry_after') + (EXTRA_DELAY_PER_PREV_RATE_LIMIT * previous_rate_limits)}s.")
    sleep(response.json().get('retry_after') + 0.5 + (EXTRA_DELAY_PER_PREV_RATE_LIMIT * previous_rate_limits))


def string_to_bool(string_input, default_value=False):
    if string_input.lower() in ["yes", "y"]:
        return True
    elif string_input.lower() in ["no", "n"]:
        return False
    return default_value


url = str(input("enter the webhook url: ") + "?wait=true")

while (get_response := get(url=url).status_code) != 200:
    print(f"the inputted url is invalid (error code {get_response} (?)), try again" + "\n")
    url = str(input("enter the webhook url: "))

    if url == "?":
        print("\n" + "401: webhook url does not exist" +
              # I DON'T THINK THIS RESPONSE IS POSSIBLE FOR THIS REQUEST, PLEASE RAISE AN ISSUE IF IT IS
              # "\n" + "403: insufficient permission for webhook" +
              "\n" + "429: you have been rate limited")
        url = str(input("\n" + "enter the webhook url: "))

content = "@everyone\n" + str(input("\n" + "enter the message to spam (automatically prepends @everyone): "))
message_amount = int(input("enter the amount of messages to spam: ") or 1)

if message_amount <= 0:
    print("'message_amount' cannot be less than or equal to 0, setting to '1'")
    message_amount = 1

content_wait = float(input("enter time between messages (enter 0 for none): ") or 0.0)

if content_wait < 0.0:
    print("'content_wait' cannot be less than 0.0, setting to '0.0'")
    content_wait = 0.0

text_to_speech_input = str(input("\n" + "enable text to speech on spammed messages? (y/n): "))
text_to_speech = string_to_bool(text_to_speech_input)

delete_webhook_input = str(input("delete webhook after spam? (y/n): "))
delete_webhook = string_to_bool(delete_webhook_input)

change_bot_identifiers_input = str(input("change bot to custom name and picture? (y/n): "))
change_bot_identifiers = string_to_bool(change_bot_identifiers_input)

if change_bot_identifiers:
    change_name_input = str(input("\n" + "change webhook name? (y/n): "))
    change_name = string_to_bool(change_name_input)

    if change_name:
        new_name = str(input("new webhook name: "))
    else:
        new_name = ""

    change_avatar_input = str(input("\n" + "change bot avatar? (y/n): "))
    change_avatar = string_to_bool(change_avatar_input)

    if change_avatar:
        new_avatar = str(input("new webhook avatar path ('.png', '.jpg', and '.jpeg' only): ")).lstrip('"').rstrip('"')
    else:
        new_avatar = ""

    update_response = update(url.strip("?wait=true"), update_payload(new_name, new_avatar))

    if update_response.status_code == 200:
        print("\n" + "modified webhook successfully!")
    elif update_response.status_code == 429:
        handle_rate_limit("update", update_response, 0)

        retry_update_response = update(url.strip("?wait=true"), update_payload(new_name, new_avatar))
        if retry_update_response.status_code == 200:
            print("\n" + "modified webhook successfully!")

messages_attempted = 0
sent = 0
delete_attempted = False
deleted = False

rate_limits = 0

print()
for i in tqdm(range(0, message_amount)):
    send_response = send(url, make_payload(content))
    messages_attempted += 1

    if send_response.status_code == 200:
        sent += 1
    elif send_response.status_code == 429:
        rate_limits += 1
        handle_rate_limit("message", send_response, rate_limits)

        retry_send_response = send(url, make_payload(content))
        if retry_send_response.status_code == 200:
            sent += 1

    if (i == message_amount - 1) and delete_webhook:
        delete_response = delete(url=url)
        delete_attempted = True

        if delete_response.status_code == 204:
            deleted = True
        elif delete_response.status_code == 429:
            rate_limits += 1
            handle_rate_limit("delete", delete_response, 0)

            retry_delete_response = delete(url=url)
            if retry_delete_response.status_code == 204:
                deleted = True

        break

    sleep(content_wait + (UNIVERSAL_DELAY_PER_PREV_RATE_LIMIT * rate_limits))

exec_command("cls") if os_name == "nt" else exec_command("clear")

print("results:" + "\n" +
      f"messages attempted: {messages_attempted}" + "\n" +
      f"messages sent: {sent}" + "\n" +
      f"delete attempted: {delete_attempted}" + "\n" +
      f"deleted: {deleted}" + "\n" +
      f"rate limits:  {rate_limits}")
input()
