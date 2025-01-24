from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import httpx
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Tokens from environment variables
TOKEN = os.getenv("TOKEN")
MYTOKEN = os.getenv("MYTOKEN")  # Verification token (prasath_token)



# Callback URL verification (GET)
@app.get("/webhook")
async def verify_webhook(request: Request):
    query_params = request.query_params
    hub_mode = query_params.get("hub.mode")
    hub_challenge = query_params.get("hub.challenge")
    hub_verify_token = query_params.get("hub.verify_token")

    print(f"hub_mode: {hub_mode}, hub_challenge: {hub_challenge}, hub_verify_token: {hub_verify_token}")
    print(f"Expected MYTOKEN: {MYTOKEN}")

    if hub_mode and hub_verify_token:
        if hub_mode == "subscribe" and hub_verify_token == MYTOKEN:
            return hub_challenge
        else:
            return {"error": "Invalid mode or token"}, 403
    return {"error": "Missing parameters"}, 400# Webhook handler (POST)

@app.post("/webhook")
async def handle_webhook(request: Request):
    """
    Handles incoming webhook POST requests.
    """
    body_param = await request.json()
    print("Received Webhook:", body_param)

    if body_param.get("object"):  # Ensure the payload has 'object'
        entry = body_param.get("entry", [])
        if entry and \
           entry[0].get("changes") and \
           entry[0]["changes"][0].get("value") and \
           entry[0]["changes"][0]["value"].get("messages") and \
           entry[0]["changes"][0]["value"]["messages"][0]:

            # Extract required data
            phone_no_id = entry[0]["changes"][0]["value"]["metadata"]["phone_number_id"]
            from_number = entry[0]["changes"][0]["value"]["messages"][0]["from"]
            msg_body = entry[0]["changes"][0]["value"]["messages"][0]["text"]["body"]

            print(f"Phone number ID: {phone_no_id}")
            print(f"From: {from_number}")
            print(f"Message body: {msg_body}")

            # Respond to the sender using WhatsApp Business API
            async with httpx.AsyncClient() as client:
                url = f"https://graph.facebook.com/v13.0/{phone_no_id}/messages"
                headers = {
                    "Content-Type": "application/json"
                }
                payload = {
                    "messaging_product": "whatsapp",
                    "to": from_number,
                    "text": {
                        "body": f"Hi.. I'm Prasath, your message is: {msg_body}"
                    }
                }

                response = await client.post(url, params={"access_token": TOKEN}, json=payload, headers=headers)
                print(f"WhatsApp API Response: {response.status_code} - {response.text}")

            return {"status": "success"}
        else:
            raise HTTPException(status_code=404, detail="Invalid body structure")
    raise HTTPException(status_code=400, detail="Bad Request")
