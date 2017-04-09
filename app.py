import os
import sys
import json
import queue

import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

inbox = queue.Queue()


@app.route('/', methods=['GET'])
def verify():
    # when the endpoint is registered as a webhook, it must echo back
    # the 'hub.challenge' value it receives in the query arguments
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == os.environ["VERIFY_TOKEN"]:
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return '<a href="https://m.me/botcycleBeta">Use me in messenger </a>', 200


@app.route('/', methods=['POST'])
def webhook():

    # endpoint for processing incoming messaging events

    data = request.get_json()
    log(data)  # you may not want to log every incoming message in production, but it's good for testing

    if data["object"] == "page":

        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:

                if messaging_event.get("message"):  # someone sent us a message

                    sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
                    recipient_id = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID
                    message_text = messaging_event["message"].get("text", None)  # the message's text (optional if e.g. thumb-up is sent)

                    inbox.put({'sender': sender_id, 'message': message_text})

                    send_message(sender_id, "got it, thanks!")

                if messaging_event.get("delivery"):  # delivery confirmation
                    pass

                if messaging_event.get("optin"):  # optin confirmation
                    pass

                if messaging_event.get("postback"):  # user clicked/tapped "postback" button in earlier message
                    pass

    return "ok", 200

@app.route('/pop_message', methods=['POST'])
def pop_message():
    if not request.headers.get("client_token", None) == os.environ["CLIENT_TOKEN"]:
        return "Client token mismatch", 403

    try:
        return jsonify(inbox.get(timeout=29)), 200
    except Exception as e:
        return "not yet", 202


@app.route('/send_message', methods=['POST'])
def send_message_routed():
    if not request.headers.get("client_token", None) == os.environ["CLIENT_TOKEN"]:
        return "Client token mismatch", 403

    data = request.get_json()

    recipient = data.get("to", None)
    message = data.get("message", None)

    if not recipient:
        return "no recipient specified", 400

    if send_message(recipient, message) != 200:
        return "error sending message", 400

    return "ok", 200

def send_message(recipient_id, message_text):

    log("sending message to {recipient}: {text}".format(recipient=recipient_id, text=message_text))

    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_text
        }
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)

    return r.status_code


def log(message):  # simple wrapper for logging to stdout on heroku
    print(str(message))
    sys.stdout.flush()


if __name__ == '__main__':
    app.run(debug=True)
