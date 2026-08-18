import cloudinary
import cloudinary.uploader

async def upload_base64_to_cloudinary(base64_string: str):
    upload_result = cloudinary.uploader.upload(
        base64_string,
        folder="messages",
        resource_type="image",
    )
    return {
        "secure_url": upload_result["secure_url"],
        "public_id": upload_result["public_id"],
    }
