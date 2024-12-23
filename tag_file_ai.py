import base64
import json
from datetime import datetime
from typing import Any, Union, Optional

import anchorpoint as ap
import apsync as aps
import os
import tempfile
import random
import openai
import hashlib

import tiktoken

from PIL import Image

local_settings = aps.Settings("ht_ai_tagger")
open_api_key = local_settings.get("openai_api_key")
if not open_api_key:
    ap.UI().show_error("No API key", "Please set up an API key in the settings")
    raise ValueError("No API key set")

os.environ["OPENAI_API_KEY"] = open_api_key

client = openai.OpenAI()

prompt = (
    "You are a file tagging AI. When asked, write tags for each file in the order they were presented: "
    "content types (texture, sprite, model, vfx, sfx, etc.), detailed genres and objects in the image"
    "Fill all 3 categories for each image. "
    "Example: \n3D Model,Texture,Sprite,Animated;Action,Adventure,RPG,Lowpoly,Metal,Steampunk;Shovel,Potion,Armor")
output_token_count = 100
input_token_price = 0.00000015
# $0.00765 for 1 million pixels
input_pixel_price = 0.00765 / 1000000
output_token_price = 0.00000016
images_per_request = 10
proceed_dialog: ap.Dialog

engines_variants = [
    ["Unity", "Unity3D", "Unity Engine"],
    ["Unreal Engine", "UE4", "UE5", "Unreal", "UE"],
    ["Godot", "Godot Engine"],
]

types_variants = [
    ["3D Model", "3D Models", "Model", "Models"],
    ["Texture", "Textures"],
    ["Sprite", "Sprites"],
    ["Animated", "Animation", "Animations"],
    [
        "VFX", "Visual Effects", "Visual Effect", "Effects", "Effect", "FX", "Visuals", "Visual", "Special Effects",
        "Special Effect"
    ],
    ["SFX", "Sound Effects", "Sound Effect", "Sound FX"],
    ["Soundtrack", "OST"],
    ["Voiceover", "VO", "Voice Over", "Voice"],
]

genres_variants: list[list[str]] = [
    ["8-Bit", "8-bit", "8 bit", "8bit"],
    ["Pixel Art", "Pixel", "Pixelated", "Pixelation", "Pixelate", "Pixel Art Style"],
    ["Lowpoly", "Low Poly", "Low-poly", "Low Polygons", "Low-Polygons", "Low Polygons Count", "Low-Polygons Count"],
    ["RPG", "Role-Playing Game", "Role Playing Game", "Roleplay", "Roleplay Game"],
    ["RTS", "Real-Time Strategy", "Real Time Strategy", "Realtime Strategy", "Realtime Strategy Game"],
    ["FPS", "First-Person Shooter", "First Person Shooter", "First-Person", "First Person"],
    ["Sci-Fi", "Science Fiction", "Science-Fiction", "SciFi", "Sci-Fi Game", "Science Fiction Game"],
]

objects_variants: list[list[str]] = []

all_variants = {
    "AI-Engines": engines_variants,
    "AI-Types": types_variants,
    "AI-Genres": genres_variants,
    "AI-Objects": objects_variants
}

response_format = {"type": "json_schema", "json_schema":
    {
        "name": "TaggingSchema",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["tags"],
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["types", "genres", "objects"],
                        "properties": {
                            "types": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "additionalProperties": False,
                                }
                            },
                            "genres": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "additionalProperties": False,
                                }
                            },
                            "objects": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "additionalProperties": False,
                                }
                            }
                        },
                    }
                }
            },
            "name": "TaggingSchema"
        }
    }}


def calculate_file_hash(file_path, hash_algorithm="sha256"):
    hash_func = hashlib.new(hash_algorithm)

    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            hash_func.update(chunk)

    return hash_func.hexdigest()


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def create_temp_directory():
    # Create a temporary directory
    temp_dir_root = os.path.join(tempfile.gettempdir(), "anchorpoint", "ai_tagger", "previews")
    if not os.path.exists(temp_dir_root):
        os.makedirs(temp_dir_root)

    return temp_dir_root


def get_preview_image(workspace_id, input_path, output_folder):
    existing_preview = aps.get_thumbnail(input_path, False)
    if existing_preview:
        print(f"Existing preview found: {existing_preview}")
        return existing_preview

    print(f"Existing preview not found for {input_path}, generating new one")

    file_hash = calculate_file_hash(input_path)

    # get the proper filename, rename it because the generated PNG file has a _pt appendix
    file_name = os.path.basename(input_path).split(".")[0]

    image_path = os.path.join(output_folder, f"{file_name}_{file_hash}_pt.png")

    if not os.path.exists(image_path):
        aps.generate_thumbnails(
            [input_path],
            output_folder,
            with_detail=False,
            with_preview=True,
            workspace_id=workspace_id,
        )
        print(f"Generated preview for {input_path}")
        os.rename(os.path.join(output_folder, f"{file_name}_pt.png"), image_path)
    else:
        print(f"Load cached preview for {input_path}")

    return image_path


def count_tokens(in_prompt, model="gpt-4o-mini"):
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(in_prompt)
    return len(tokens)


def get_openai_response_images(in_prompt, image_paths: list[str], model="gpt-4o-mini") -> list[Any]:
    if len(image_paths) == 0 or len(image_paths) > images_per_request:
        raise ValueError(f"The number of images should be between 1 and {images_per_request}")

    uploads_base64 = []
    for image_path in image_paths:
        uploads_base64.append(encode_image(image_path))

    try:
        original_file_names = []
        for image_path in image_paths:
            original_file_names.append(os.path.basename(original_files[image_path]))
        content = [{
            "type": "text",
            "text": "Please tag these images: " + ", ".join(original_file_names)
        }]
        print(content)
        for upload in uploads_base64:
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{upload}"}, })

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": in_prompt},
                {

                    "role": "user",
                    "content": content
                }
            ],
            response_format=response_format
        )

        result = response.choices[0].message.content.strip()
        parsed = json.loads(result)
        return parsed['tags']
    except openai.OpenAIError as e:
        print(f"Error: {e}")
        return []


def replace_tag(tag: str, variants: list[list[str]]) -> str:
    if not variants:
        return tag
    for variant in variants:
        if tag in variant:
            return variant[0]

    return tag


def ensure_attribute(database: aps.Api, attribute_name: str) -> aps.Attribute:
    attribute = database.attributes.get_attribute(attribute_name)
    if not attribute:
        attribute = database.attributes.create_attribute(
            attribute_name, aps.AttributeType.multiple_choice_tag
        )
    return attribute


previews_sliced = []
original_files: dict[str, str] = {}


def check_or_update_attribute(attribute: aps.Attribute, tag: str, database: aps.Api):
    anchorpoint_tags = attribute.tags
    colors = [
        "grey", "blue", "purple", "green",
        "turk", "orange", "yellow", "red"]

    # Create a set of anchorpoint tag names for faster lookup
    anchorpoint_tag_names = {a_tag.name for a_tag in anchorpoint_tags}
    if tag not in anchorpoint_tag_names:
        new_tag = aps.AttributeTag(tag, random.choice(colors))
        anchorpoint_tags.append(new_tag)
        database.attributes.set_attribute_tags(attribute, anchorpoint_tags)
        return new_tag

    for a_tag in anchorpoint_tags:
        if a_tag.name == tag:
            return a_tag

    raise ValueError(f"Tag {tag} not found in the attribute tags: {anchorpoint_tag_names}")


def change_slices_to_skip(database):
    new_previews = []
    prev_count = 0

    global previews_sliced
    for p in previews_sliced:
        for preview in p:
            original_file = original_files[preview]
            prev_count += 1
            ai_types_attr: Union[aps.apsync.Attribute, str] = database.attributes.get_attribute_value(
                original_file,
                "AI-Types")
            if ai_types_attr and len(ai_types_attr) > 0:
                continue

            new_previews.append(preview)

    new_previews_sliced = [
        new_previews[i:i + images_per_request] for i in
        range(0, len(new_previews), images_per_request)]
    print(f"Reduced previews from {prev_count} to {len(new_previews)}")
    previews_sliced = new_previews_sliced


def proceed_callback(database):
    proceed_dialog.close()
    skip_existing_tags = proceed_dialog.get_value("skip_existing_tags")
    if skip_existing_tags:
        change_slices_to_skip(database)

    def run():
        progress = ap.Progress("Requesting AI tags", "Processing", infinite=False, show_loading_screen=True)
        global start_time
        start_time = datetime.now()
        print(f"Started tagging {len(previews_sliced)} previews")
        progress.report_progress(0)
        for i, p in enumerate(previews_sliced):
            response = get_openai_response_images(prompt, p)
            progress.report_progress((i + 1) / len(previews_sliced))
            print(response)
            if len(response) < len(p):
                ap.UI().navigate_to_folder(initial_folder)
                ap.UI().show_error(
                    "Error", f"Not all images were tagged [Received {len(response)}, requested {len(p)}]")
                raise ValueError(f"Not all images were tagged [Received {len(response)}, requested {len(p)}]")

            progress2 = ap.Progress("Updating tags", "Processing", infinite=False, show_loading_screen=True)
            for j, preview in enumerate(p):
                progress2.report_progress(j / len(p))
                tags = response[j]

                ap.UI().navigate_to_folder(os.path.dirname(original_files[p[j]]))

                types = tags["types"]
                types_tags = aps.AttributeTagList()
                for k, tag in enumerate(types):
                    types[k] = replace_tag(tag, all_variants["AI-Types"])
                    new_tag = check_or_update_attribute(attributes[0], types[k], database)
                    types_tags.append(new_tag)

                database.attributes.set_attribute_value(original_files[p[j]], "AI-Types", types_tags)

                genres = tags["genres"]
                genres_tags = aps.AttributeTagList()

                for k, tag in enumerate(genres):
                    genres[k] = replace_tag(tag, all_variants["AI-Genres"])
                    new_tag = check_or_update_attribute(attributes[1], genres[k], database)
                    genres_tags.append(new_tag)

                objects = tags["objects"]
                objects_tags = aps.AttributeTagList()

                database.attributes.set_attribute_value(original_files[p[j]], "AI-Genres", genres_tags)

                for k, tag in enumerate(objects):
                    objects[k] = replace_tag(tag, all_variants["AI-Objects"])
                    new_tag = check_or_update_attribute(attributes[2], objects[k], database)
                    objects_tags.append(new_tag)

                database.attributes.set_attribute_value(original_files[p[j]], "AI-Objects", objects_tags)
            progress2.finish()

        progress.finish()
        finish_time = datetime.now()
        print(f"Finished tagging in {finish_time - start_time}")
        ap.UI().navigate_to_folder(initial_folder)

    ctx = ap.get_context()
    ctx.run_async(run)


previews = []
file_input_paths = []
last_index = -1
generating_previews_count = 0
generating_previews_progress: Optional[ap.Progress] = None
ap_context: Optional[ap.Context] = None
start_time = datetime.now()


def proceed_generating_previews(workspace_id, database, output_folder):
    if generating_previews_count > len(file_input_paths):
        return

    if generating_previews_count == len(file_input_paths):
        finish_generating_previews(previews, database)
        return

    if last_index >= len(file_input_paths) - 1:
        return

    input_path = file_input_paths[last_index + 1]
    generate_preview_async(workspace_id, input_path, output_folder, database)
    # ap_context.run_async(generate_preview_async, workspace_id, input_path, output_folder, database)


def generate_previews(workspace_id, input_paths, database):
    if len(input_paths) == 0:
        ap.UI().navigate_to_folder(initial_folder)
        ap.UI().show_error("No supported files selected", "Please select files to tag")
        print("No supported files selected")
        return

    global start_time
    start_time = datetime.now()
    print(f"Started generating previews for {len(input_paths)} files")

    # start progress
    global generating_previews_progress
    generating_previews_progress = ap.Progress(
        "Generating previews", "Processing", infinite=False,
        show_loading_screen=True)
    output_folder = create_temp_directory()

    global previews
    previews = []
    global file_input_paths
    file_input_paths = input_paths
    print("Output folder: {}".format(output_folder.replace("\\", "\\\\")))
    global ap_context
    ap_context = ap.get_context()
    proceed_generating_previews(workspace_id, database, output_folder)
    # start generating first 10 previews
    for i in range(min(images_per_request, len(input_paths))):
        input_path = input_paths[i]
        ap_context.run_async(generate_preview_async, workspace_id, input_path, output_folder, database)


def generate_preview_async(workspace_id, input_path, output_folder, database):
    global last_index
    if last_index >= len(file_input_paths) - 1:
        return
    last_index += 1
    image_path = get_preview_image(workspace_id, input_path, output_folder)
    previews.append(image_path)
    original_files[image_path] = input_path

    global generating_previews_count
    generating_previews_count += 1

    generating_previews_progress.report_progress(generating_previews_count / len(file_input_paths))
    proceed_generating_previews(workspace_id, database, output_folder)


def finish_generating_previews(input_paths, database):
    generating_previews_progress.finish()
    print(f"Finished generating previews for {len(input_paths)} files")
    current_time = datetime.now()
    print(f"Generated {len(input_paths)} previews in {current_time - start_time}")
    process_images(input_paths, database)


def process_images(input_paths, database):
    # calculate pixel count
    pixel_count = 0
    asset_names = []
    progress = ap.Progress("Calculating pixel count", "Processing", infinite=False, show_loading_screen=True)
    for i, preview_path in enumerate(previews):
        image = Image.open(preview_path)

        # trim transparent pixels
        box = image.getbbox()
        image = image.crop(box)
        image.save(preview_path)

        width, height = image.size
        if width > 256 or height > 256:
            # resize image
            image.thumbnail((256, 256))
            image.save(preview_path)
            width, height = image.size
        pixel_count += width * height
        progress.report_progress(i / len(previews))
        asset_names.append(os.path.basename(original_files[preview_path]))

    global previews_sliced
    # slice previews by images_per_request
    previews_sliced = [previews[i:i + images_per_request] for i in range(0, len(previews), images_per_request)]

    # calculate token count
    pixel_price = pixel_count * input_pixel_price
    print(f"Pixel count: {pixel_count}")
    print(f"Pixel price: {pixel_price}")
    progress.finish()
    token_count = count_tokens(prompt + ", ".join(asset_names))
    total_tokens = token_count * len(previews_sliced)
    combined_output_tokens = len(previews) * output_token_count

    total_price = total_tokens * input_token_price + pixel_price + combined_output_tokens * output_token_price

    global proceed_dialog
    proceed_dialog = ap.Dialog()
    proceed_dialog.title = "AI Tags for files"
    proceed_dialog.add_text(f"Processing files: {len(input_paths)}"
                            f"\nInput token count: {total_tokens}"
                            f"\nOutput token count: ~{combined_output_tokens}"
                            f"\nPixel count: {pixel_count}"
                            f"\nPrice: ~${total_price}"
                            f"\n\nProceed?")
    proceed_dialog.add_checkbox(False, None, var="skip_existing_tags").add_text("Skip existing tags")
    (
        proceed_dialog
        .add_button("OK", callback=lambda d: proceed_callback(database))
        .add_button("Cancel", callback=lambda d: d.close(), primary=False)
    )
    proceed_dialog.show()


attributes = []


def filter_ignored_extensions(files: list[str], ignored_ext: list[list[str]]) -> list[str]:
    filtered_files = []
    for file in files:
        file_ext = file.split(".")[-1]
        for ignored_extension in ignored_ext:
            if file_ext in ignored_extension:
                print(f"Ignoring file because of extension: {file}")
                break
        else:
            filtered_files.append(file)

    return filtered_files


ignored_unity_extensions = [
    "meta", "unity", "prefab", "asset", "mat", "controller", "anim", "mask",
    "overrideController", "physicMaterial", "physicsMaterial2D", "renderTexture", "shader",
    "cubemap", "flare", "giparams", "lightingData", "unitypackage"
]
ignored_unreal_extensions = [
    "umap", "uplugin", "uproject", "uexp", "upk", "udk", "uc", "u", "udata", "uclass",
    "ustruct", "ufunction", "uinterface", "uenum", "uproperty"
]
ignored_godot_extensions = [
    "tscn", "tres", "import", "scn", "res", "gd", "gdc", "gdscript", "gdn"
]
ignored_temp_extensions = [
    "tmp", "temp", "bak", "backup", "old", "cache", "log", "lock", "swp"
]
ignored_audio_extensions = [
    "mp3", "wav", "ogg", "flac", "aiff", "aif", "wma", "m4a", "aac", "mid", "midi", "mod", "xm", "it", "s3m", "flp",
]
ignored_extensions = [
    ignored_unity_extensions, ignored_unreal_extensions, ignored_godot_extensions,
    ignored_temp_extensions, ignored_audio_extensions
]


def get_all_files_recursive(folder_path) -> list[str]:
    files = []
    for root, _, file_names in os.walk(folder_path):
        for file_name in file_names:
            files.append(str(os.path.join(root, file_name)))

    return files


initial_folder = ""


def main():
    ctx = ap.get_context()
    database = ap.get_api()
    # Create or get the "AI Tags" attributes
    types_attribute = ensure_attribute(database, "AI-Types")
    genres_attribute = ensure_attribute(database, "AI-Genres")
    objects_attribute = ensure_attribute(database, "AI-Objects")

    global attributes
    attributes = [types_attribute, genres_attribute, objects_attribute]

    selected_files = ctx.selected_files

    selected_folders = ctx.selected_folders

    print(selected_folders)

    if len(selected_folders) > 0:
        for folder in selected_folders:
            inner_files = get_all_files_recursive(folder)
            print(inner_files)
            selected_files.extend(inner_files)

    filtered_files = filter_ignored_extensions(selected_files, ignored_extensions)

    global initial_folder
    initial_folder = ctx.path

    ctx.run_async(generate_previews, ctx.workspace_id, filtered_files, database)
    return


if __name__ == "__main__":
    main()
