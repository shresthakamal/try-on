import os
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Initialize FastAPI app
app = FastAPI()

from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

# Initialize Twilio client with environment variables for account SID and auth token
client = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])

from try_on.download import download_images_from_twilio

# In-memory cache to store user-related data
cache: dict[str, dict[str, dict[str, str]]] = {}


@app.get("/")
def index() -> dict[str, str]:
    """
    Basic endpoint to check if the service is running.
    """
    return {"message": "TRY ON"}


# if media directory does not exist, create it
if not os.path.exists("media"):
    os.makedirs("media")

# Mounting the /media directory to serve images to Twilio
app.mount("/media", StaticFiles(directory="media"), name="media")


@app.get("/media/{filename}")
async def serve_media_file(filename: str) -> FileResponse:
    """
    Serve the media file (image) stored in the /media directory.

    Args:
        filename (str): Name of the file to be served.

    Returns:
        FileResponse: The media file response.

    Raises:
        HTTPException: If the file does not exist, raises a 404 error.
    """
    file_path = os.path.join("media", filename)

    # Check if the file exists and serve it
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="image/png")
    else:
        print(f"File not found: {filename}")
        raise HTTPException(status_code=404, detail="File not found")


@app.post("/tryon")
async def tryon(request: Request) -> Response:
    """
    Handle the image processing for the virtual try-on.

    Args:
        request (Request): The incoming request containing media and user information.

    Returns:
        Response: The response in XML format for Twilio messaging API.
    """
    # Extract form data from the incoming request
    requestBody = await request.form()

    sender: str = requestBody.get("From")
    receiver: str = requestBody.get("To")
    user: str = requestBody.get("AccountSid")

    # Initialize user cache if not present
    if user not in cache:
        cache[user] = {}

    print("=============================================")
    print(f"[FROM] : {sender} : {user}")
    print(f"[TO]: {receiver}")
    print(f"[MESSAGE] : {requestBody.get('Body')}")
    print("=============================================")

    # Handle case where no media is received
    if requestBody.get("NumMedia") == "0":
        response = MessagingResponse()
        response.message(
            "We didn't receive an image. Please try sending your image again."
        )
        return Response(content=str(response), media_type="application/xml")

    # Extract media URL and process images
    media_url = requestBody.get("MediaUrl0")

    # Handle the first image (person)
    if "person" not in cache[user]:
        cache[user]["person"] = {
            "url": media_url,
            "MessageSid": requestBody.get("MessageSid"),
            "MediaId": media_url.split("/")[-1],
        }

        # Prompt the user for the second image (product)
        response = MessagingResponse()
        response.message(
            "We have received your image. Please send the image of the product you want to try on."
        )
        return Response(content=str(response), media_type="application/xml")

    # Handle the second image (product)
    if "product" not in cache[user]:
        cache[user]["product"] = {
            "url": media_url,
            "MessageSid": requestBody.get("MessageSid"),
            "MediaId": media_url.split("/")[-1],
        }

    # Check if both images (person and product) are received
    if "person" in cache[user] and "product" in cache:
        print("Both images received. Processing the images now...")

    # Download images from Twilio and save them locally
    if not os.path.exists(f"media/{user}"):
        os.makedirs(f"media/{user}")

    personPath = await download_images_from_twilio(
        client, cache[user]["person"], f"media/{user}/person.jpg"
    )
    productPath = await download_images_from_twilio(
        client, cache[user]["product"], f"media/{user}/product.jpg"
    )

    # Generate prediction using Gradio API
    from try_on.predict import predict

    predictionStatus = await predict(personPath, productPath, user)

    # Send response based on prediction status
    if predictionStatus:
        # Send success message with prediction image
        client.messages.create(
            from_=receiver,
            body="Well, well, well, you are looking pretty nice !!!",
            media_url=[f"{os.environ['NGROK_URL']}/media/{user}/prediction.png"],
            to=sender,
        )
        response = MessagingResponse()
        return Response(content=str(response), media_type="application/xml")

    # If something went wrong with the try-on process
    else:
        response = MessagingResponse()
        response.message("Sorry, something went wrong with the try-on process.")
        return Response(content=str(response), media_type="application/xml")
