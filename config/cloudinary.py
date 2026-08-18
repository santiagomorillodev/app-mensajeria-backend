from dotenv import load_dotenv
from os import getenv
import cloudinary

load_dotenv()

cloudinary.config(
    cloud_name = getenv('CLOUDINARY_NAME'),
    api_key = getenv('CLOUDINARY_API_KEY'),
    api_secret = getenv('CLOUDINARY_API_SECRET')
)