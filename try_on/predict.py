import os
import cv2
from gradio_client import Client as GradioClient, handle_file


async def predict(person: str, product: str, user: str) -> bool:
    """
    Uses a Gradio-based Virtual Try-On model to generate a prediction image.

    Args:
        person (str): The path to the person's image.
        product (str): The path to the product's image.
        user (str): The unique identifier for the user (used for saving the prediction).

    Returns:
        bool: Returns True if the prediction image is successfully created, False otherwise.
    """

    # Check if the prediction image already exists to avoid unnecessary reprocessing
    if os.path.exists(f"media/{user}/prediction.png"):
        print(f"Prediction already exists for {user}.")
        return True

    # Initialize the Gradio client for the Virtual Try-On model
    client = GradioClient("Nymbo/Virtual-Try-On")

    # Make a prediction using the Gradio model
    response = client.predict(
        dict={
            "background": handle_file(person),  # The person's image
            "layers": [],  # Layers for additional customization (empty in this case)
            "composite": None,  # No composite image
        },
        garm_img=handle_file(product),  # The product image to try on
        garment_des="Garment for the user to try on",  # Description of the garment
        is_checked=True,  # Indicating the user wants the try-on
        is_checked_crop=False,  # Don't crop the images
        denoise_steps=30,  # Number of denoise steps
        seed=42,  # Random seed for consistency
        api_name="/tryon",  # The API endpoint to call for prediction
    )

    # If the prediction is successful, save the image to the user's directory
    if response:
        # Read the generated prediction image
        img = cv2.imread(response[0])

        # Save the prediction image in the 'media/{user}' directory
        cv2.imwrite(f"media/{user}/prediction.png", img)

        return True
    else:
        print(f"Prediction failed for {user}.")
        return False
