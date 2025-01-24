from flask import Flask, request, jsonify
import asyncio
import httpx
import os
from flasgger import Swagger

app = Flask(__name__)

# Initialize Swagger UI
swagger = Swagger(app)

# Replace with your actual environment variables
WEBHOOK_VERIFY_TOKEN = os.environ.get('MYTOKEN')
GRAPH_API_TOKEN = os.environ.get('TOKEN')  # Use environment variables for security
IMAGE_STORAGE_PATH = os.environ.get('IMAGE_STORAGE_PATH', './images')

@app.route("/webhook", methods=["GET", "POST"])
async def webhook():
    """
    Webhook for WhatsApp incoming messages
    ---
    get:
      description: Verify the webhook
      parameters:
        - name: hub.mode
          in: query
          required: true
          type: string
        - name: hub.verify_token
          in: query
          required: true
          type: string
        - name: hub.challenge
          in: query
          required: true
          type: string
      responses:
        200:
          description: Verification successful
        403:
          description: Invalid verification request
    post:
      description: Process incoming messages and send echo reply
      parameters:
        - name: data
          in: body
          required: true
          schema:
            type: object
            properties:
              entry:
                type: array
                items:
                  type: object
                  properties:
                    changes:
                      type: array
                      items:
                        type: object
                        properties:
                          value:
                            type: object
                            properties:
                              messages:
                                type: array
                                items:
                                  type: object
                                  properties:
                                    from:
                                      type: string
                                    text:
                                      type: object
                                      properties:
                                        body:
                                          type: string
      responses:
        200:
          description: Message received and processed
        500:
          description: Error processing message
    """
    if request.method == 'GET':
        # Verification of the webhook (GET request)
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

        # Check if the token matches
        if mode == "subscribe" and token == WEBHOOK_VERIFY_TOKEN:
            return challenge, 200
        else:
            return "Invalid verification request", 403

    elif request.method == 'POST':
        # Processing incoming WhatsApp messages (POST request)
        data = request.get_json()

        try:
            # Extract the incoming message details
            message = data['entry'][0]['changes'][0]['value'].get('messages', [])[0]
            sender_id = message['from']

            if 'text' in message:
                # Handle text messages
                message_text = message['text']['body']
                print(f"Received text message from {sender_id}: {message_text}")

                # Send echo reply for text
                response_data = {
                    "messaging_product": "whatsapp",
                    "to": sender_id,
                    "text": {"body": f"Echo: {message_text}"}
                }

            elif 'image' in message:
                # Handle image messages
                image_id = message['image']['id']
                print(f"Received image message from {sender_id}, Image ID: {image_id}")

                # Download and store the image
                await download_and_store_image(image_id)

                # Reply acknowledging the image
                response_data = {
                    "messaging_product": "whatsapp",
                    "to": sender_id,
                    "text": {"body": "Thanks for sending the image!"}
                }

            else:
                # Handle unsupported message types
                print(f"Unsupported message type from {sender_id}.")
                return "Unsupported message type received.", 200

            # Send reply
            headers = {
                "Authorization": f"Bearer {GRAPH_API_TOKEN}"
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://graph.facebook.com/v18.0/me/messages",
                    headers=headers,
                    json=response_data
                )

                if response.status_code == 200:
                    print("Reply sent successfully.")
                else:
                    print(f"Failed to send reply. Status code: {response.status_code}")

            return "Message received and processed.", 200

        except Exception as e:
            print(f"Error processing message: {e}")
            return "Error processing message.", 500


async def download_and_store_image(image_id):
    """Download an image using its ID and store it."""
    try:
        # Fetch image URL
        async with httpx.AsyncClient() as client:
            url_response = await client.get(
                f"https://graph.facebook.com/v18.0/{image_id}",
                headers={"Authorization": f"Bearer {GRAPH_API_TOKEN}"}
            )
            url_response.raise_for_status()
            image_url = url_response.json().get('url')
            if not image_url:
                raise ValueError("Image URL not found in response.")

            # Download the image
            image_response = await client.get(image_url)
            image_response.raise_for_status()

            # Save the image to the storage path
            os.makedirs(IMAGE_STORAGE_PATH, exist_ok=True)
            image_path = os.path.join(IMAGE_STORAGE_PATH, f"{image_id}.jpg")
            with open(image_path, "wb") as f:
                f.write(image_response.content)

            print(f"Image saved to {image_path}")

    except Exception as e:
        print(f"Failed to download or store image: {e}")


if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()  # To allow asyncio in Flask debug mode
    app.run(debug=True, port=5000)
