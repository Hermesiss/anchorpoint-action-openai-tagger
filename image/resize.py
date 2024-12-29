from PIL import Image


def resize_image(image_path: str, max_dimension: int) -> list[int]:
    """
    Resize an image to the specified maximum dimension, preserving aspect ratio.
    :param image_path: Path to the image file
    :param max_dimension: Maximum dimension for the resized image
    :return list[int]: Width and height of the resized image
    """
    image = Image.open(image_path)

    # trim transparent pixels
    box = image.getbbox()
    image = image.crop(box)
    image.save(image_path)

    width, height = image.size
    if width > max_dimension or height > max_dimension:
        # resize image
        image.thumbnail((max_dimension, max_dimension))
        image.save(image_path)
        width, height = image.size

    return [width, height]
