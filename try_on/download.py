import os
import requests
from twilio.rest import Client


async def download_images_from_twilio(
    client: Client, imageData: dict[str, str], filename: str
) -> str | None:
    """
    Downloads an image from Twilio if it has not been downloaded already.

    Args:
        client (Client): The Twilio client used to make API requests.
        imageData (dict[str, str]): A dictionary containing the image data (URL, MessageSid, MediaId).
        filename (str): The filename where the image will be saved.

    Returns:
        str | None: Returns the filename if the image is downloaded successfully, otherwise None.
    """
    # Check if the image is already downloaded
    if os.path.exists(filename):
        print(f"Image already exists as {filename}.")
        return filename

    print(f"Downloading image {filename} from Twilio.")

    # Extract image information from imageData
    media_url = imageData["url"]
    message_sid = imageData["MessageSid"]
    media_id = imageData["MediaId"]

    # Fetch media information using the Twilio API
    media = (
        client.api.accounts(os.environ["TWILIO_ACCOUNT_SID"])
        .messages(message_sid)
        .media(media_id)
        .fetch()
    )

    # Construct the actual media URL
    media_uri = media.uri.replace(".json", "")

    # Send a GET request to fetch the image from Twilio
    response = requests.get(
        f"https://api.twilio.com{media_uri}",
        auth=(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"]),
    )

    # Check if the response status code is 200 (success)
    if response.status_code == 200:
        print(f"Image downloaded successfully as {filename}.")

        # Write the image content to the file
        with open(filename, "wb") as f:
            f.write(response.content)

        return filename
    else:
        print(f"Failed to download image: {response.status_code}")
        return None
