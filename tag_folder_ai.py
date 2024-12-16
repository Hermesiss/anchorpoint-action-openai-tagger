# This example demonstrates how to create a simple dialog in Anchorpoint
from typing import Any

import anchorpoint as ap
import apsync as aps
import os
import tempfile
import random
import openai

import tiktoken

prompt = (
    "Write tags for the folder: required game engines (if it has e.g. uasset or unitypackage) or 'All' if assets have common types, "
    "content types (texture, sprite, model, vfx, sfx, etc.), and detailed genres."
    "Use commas within categories and semicolons between categories.\n"
    "Do not include any prefixes or additional text in the response, only the tags.\n"
    "Example: \nUnity,Unreal Engine;3D Model,Texture,Sprite,Animated;Action,Adventure,RPG,Lowpoly,Metal,Steampunk,\n")
output_token_count = 100
input_token_price = 0.00000015
output_token_price = 0.00000016
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

genres_variants: list[list[str]] = []

all_variants = {
    "AI-Engines": engines_variants,
    "AI-Types": types_variants,
    "AI-Genres": genres_variants,
}


def get_folder_structure(input_path) -> dict[Any, list[Any]]:
    folder_structure = {}
    for root, dirs, files in os.walk(input_path):
        folder_structure[root] = files

    return folder_structure


def count_tokens(in_prompt, model="gpt-4o-mini"):
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(in_prompt)
    return len(tokens)


def tag_folders(workspace_id: str, input_paths: list[str], database: aps.Api, attributes: list[aps.Attribute]):
    folders = []

    for input_path in input_paths:
        if os.path.isdir(input_path):
            folder_structure = get_folder_structure(input_path)
            folder_structure_str = str(folder_structure)
            folder_name = os.path.basename(input_path)
            # replace input_path with "root"
            folder_structure_str = folder_structure_str.replace(input_path, "root")
            print(folder_structure_str)

            full_prompt = f"{prompt}\nFolder name: {folder_name}\nFolder structure:\n{folder_structure_str}"
            print(full_prompt)
            token_count = count_tokens(full_prompt)
            input_price = token_count * input_token_price
            folders.append((input_path, full_prompt, token_count, input_price))

    global proceed_dialog
    proceed_dialog = ap.Dialog()
    proceed_dialog.title = "AI Tags"
    if len(folders) == 1:
        proceed_dialog.title += " - " + os.path.basename(folders[0][0])
    else:
        proceed_dialog.title += f" - {len(folders)} folders"

    combined_tokens = sum([folder[2] for folder in folders])
    combined_output_tokens = len(folders) * output_token_count
    combined_input_price = sum([folder[3] for folder in folders])
    combined_output_price = combined_output_tokens * output_token_price
    proceed_dialog.add_text(f"Input token count: {combined_tokens}"
                            f"\nOutput token count: ~{combined_output_tokens}"
                            f"\nPrice: ~${combined_input_price + combined_output_price}"
                            f"\n\nProceed?")
    proceed_dialog.add_button(
        "OK", callback=lambda d: proceed_callback(folders, workspace_id, database, attributes))
    proceed_dialog.add_button("Cancel", callback=lambda d: d.close(), primary=False)
    proceed_dialog.show()


def proceed_callback(
        folders: list[tuple[str, str, int, float]], workspace_id: str, database: aps.Api,
        attributes: list[aps.Attribute]):
    proceed_dialog.close()

    def run():
        progress = ap.Progress("Requesting AI tags", "Processing", infinite=False, show_loading_screen=True)
        progress.report_progress(0)
        for i, folder in enumerate(folders):
            tag_folder(folder[1], folder[0], workspace_id, database, attributes)
            progress.report_progress((i + 1) / len(folders))
        progress.finish()

    ctx = ap.get_context()
    ctx.run_async(run)


def get_openai_response(in_prompt, model="gpt-4o-mini"):
    try:
        # Create a chat completion request
        response = openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": in_prompt}
            ],
            max_tokens=100,
        )
        # Extract and return the response content
        return response.choices[0].message.content.strip()
    except openai.OpenAIError as e:
        return f"Error: {e}"


def replace_tag(tag: str, variants: list[list[str]]) -> str:
    if not variants:
        return tag
    for variant in variants:
        if tag in variant:
            return variant[0]

    return tag


def tag_folder(
        full_prompt: str, input_path: str, workspace_id: str, database: aps.Api,
        attributes: list[aps.Attribute]):
    response = get_openai_response(full_prompt)
    print(response)

    tags = response.split(";")
    if len(tags) != len(attributes):
        ap.UI().show_error(
            "Error",
            f"The number of categories ({len(tags)}) does not match the number of attributes ({len(attributes)})")
        return

    for i, tag in enumerate(tags):
        attribute = attributes[i]
        anchorpoint_tags = attribute.tags

        colors = [
            "grey", "blue", "purple", "green",
            "turk", "orange", "yellow", "red"]

        # Create a set of anchorpoint tag names for faster lookup
        anchorpoint_tag_names = {tag.name for tag in anchorpoint_tags}

        # Add new tags from image_tags that are not already in anchorpoint_tag_names
        folder_tags = tag.split(",")
        replaced_tags = []

        for folder_tag in folder_tags:
            tag = replace_tag(folder_tag.strip(), all_variants[attribute.name])
            if not tag in replaced_tags:
                replaced_tags.append(tag)

        for folder_tag in replaced_tags:
            folder_tag = folder_tag
            if folder_tag not in anchorpoint_tag_names:
                new_tag = aps.AttributeTag(folder_tag, random.choice(colors))
                anchorpoint_tags.append(new_tag)

        # Update the attribute tags in the database
        database.attributes.set_attribute_tags(attribute, anchorpoint_tags)

        ao_tags = aps.AttributeTagList()
        for anchorpoint_tag in anchorpoint_tags:
            if anchorpoint_tag.name in replaced_tags:
                ao_tags.append(anchorpoint_tag)

        # Set the attribute value for the input path
        database.attributes.set_attribute_value(input_path, attribute, ao_tags)


def ensure_attribute(database: aps.Api, attribute_name: str) -> aps.Attribute:
    attribute = database.attributes.get_attribute(attribute_name)
    if not attribute:
        attribute = database.attributes.create_attribute(
            attribute_name, aps.AttributeType.multiple_choice_tag
        )
    return attribute


def main():
    ctx = ap.get_context()
    database = ap.get_api()
    # Create or get the "AI Tags" attribute
    engines_attribute = ensure_attribute(database, "AI-Engines")
    types_attribute = ensure_attribute(database, "AI-Types")
    genres_attribute = ensure_attribute(database, "AI-Genres")

    attributes = [engines_attribute, types_attribute, genres_attribute]

    selected_folders = ctx.selected_folders
    if len(selected_folders) == 0:
        selected_folders = [ctx.path]

    ctx.run_async(
        tag_folders, ctx.workspace_id,
        selected_folders, database, attributes)


if __name__ == "__main__":
    main()
