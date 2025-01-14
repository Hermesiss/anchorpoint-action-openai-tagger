# This example demonstrates how to create a simple dialog in Anchorpoint
import json
from typing import Any

import anchorpoint as ap
import apsync as aps
import os
import random

import requests

from ai.api import init_openai_key, OPENAI_API_URL
from ap_tools.dialogs import CreateTagFoldersDialogData, create_tag_folders_dialog
from ap_tools.logging import log, log_err
from labels.attributes import ensure_attribute, replace_tag, attribute_colors
from labels.variants import engines_variants, types_variants, genres_variants

from ai.constants import input_token_price, output_token_price
from ai.tokens import count_tokens

from package_settings import TaggerSettings

settings = TaggerSettings()

prompt = "Write tags for the folder:"

if settings.folder_use_ai_engines:
    prompt += "required game engines (e.g. UE if it has *.uasset or Unity if it has *.unitypackage) or 'All' if assets have common types, "

if settings.folder_use_ai_types:
    prompt += "content types (Texture, Sprite, Model, VFX, SFX, etc.), "

if settings.folder_use_ai_genres:
    prompt += "detailed genres, "

prompt += "fill all tags"

output_token_count = 200

proceed_dialog: ap.Dialog

all_variants = {
    "AI-Engines": engines_variants,
    "AI-Types": types_variants,
    "AI-Genres": genres_variants,
}

items = {
    "type": "object",
    "additionalProperties": False,
    "required": [],
    "properties": {}
}

if settings.folder_use_ai_engines:
    items["required"].append("engines")
    items["properties"]["engines"] = {
        "type": "array",
        "items": {
            "type": "string",
            "additionalProperties": False,
        }
    }

if settings.folder_use_ai_types:
    items["required"].append("types")
    items["properties"]["types"] = {
        "type": "array",
        "items": {
            "type": "string",
            "additionalProperties": False,
        }
    }

if settings.folder_use_ai_genres:
    items["required"].append("genres")
    items["properties"]["genres"] = {
        "type": "array",
        "items": {
            "type": "string",
            "additionalProperties": False,
        }
    }

response_format = {"type": "json_schema", "json_schema":
    {
        "name": "TaggingSchema",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["items"],
            "properties": {
                "items": items
            },
            "name": "TaggingSchema"
        }
    }}


def get_folder_structure(input_path) -> dict[Any, list[Any]]:
    folder_structure = {}
    for root, dirs, files in os.walk(input_path):
        folder_structure[root] = files

    return folder_structure


def tag_folders(workspace_id: str, input_paths: list[str], database: aps.Api, attributes: list[aps.Attribute]):
    folders = []
    progress = ap.Progress("Counting tokens", "Processing", infinite=False, show_loading_screen=True)

    total_steps = 3
    for i, input_path in enumerate(input_paths):
        if os.path.isdir(input_path):
            folder_structure = get_folder_structure(input_path)
            progress.report_progress(i / len(input_paths) + (1 / total_steps / len(input_paths)))
            folder_structure_str = str(folder_structure)
            folder_name = os.path.basename(input_path)
            # replace input_path with "root"
            folder_structure_str = folder_structure_str.replace(input_path, "root")
            progress.report_progress(i / len(input_paths) + (2 / total_steps / len(input_paths)))
            log(folder_structure_str)

            full_prompt = f"{prompt}\nFolder name: {folder_name}\nFolder structure:\n{folder_structure_str}"
            log(full_prompt)
            token_count = count_tokens(full_prompt)
            progress.report_progress(i / len(input_paths) + (3 / total_steps / len(input_paths)))
            input_price = token_count * input_token_price
            folders.append((input_path, full_prompt, token_count, input_price))

    progress.finish()
    global proceed_dialog
    data = CreateTagFoldersDialogData(folders, output_token_count, output_token_price)
    proceed_dialog = create_tag_folders_dialog(
        data,
        lambda d: proceed_callback(folders, workspace_id, database, attributes))
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


OPENAI_API_KEY = init_openai_key()


def get_openai_response(in_prompt, model="gpt-4o-mini") -> dict:
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a folder tagging AI."},
            {"role": "user", "content": in_prompt}
        ],
        "response_format": response_format
    }

    log(f"Body: {payload}")

    try:
        response = requests.post(OPENAI_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        result_content = result["choices"][0]["message"]["content"].strip()
        parsed = json.loads(result_content)
        return parsed["items"]
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}
    except KeyError:
        return {"error": "No response from OpenAI"}


def tag_folder(
        full_prompt: str, input_path: str, workspace_id: str, database: aps.Api,
        attributes: list[aps.Attribute]):
    response = get_openai_response(full_prompt)
    log(response)
    if response.get("error"):
        err = f"Error while tagging folder: {response['error']}"
        ap.UI().show_error("Error", err)
        log_err(err)
        return

    tags = [response["engines"], response["types"], response["genres"]]
    if len(tags) != len(attributes):
        err = f"The number of categories ({len(tags)}) does not match the number of attributes ({len(attributes)})"
        ap.UI().show_error("Error", err)
        log_err(err)
        return

    for i, tag in enumerate(tags):
        attribute = attributes[i]
        anchorpoint_tags = attribute.tags

        colors = attribute_colors

        # Create a set of anchorpoint tag names for faster lookup
        anchorpoint_tag_names = {tag.name for tag in anchorpoint_tags}

        # Add new tags from image_tags that are not already in anchorpoint_tag_names
        folder_tags = tag
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


def main():
    if not settings.any_folder_tags_selected():
        ap.UI().show_error("No tags selected", "Please select at least one tag category in the settings")
        return

    ctx = ap.get_context()
    database = ap.get_api()

    engines_attribute = ensure_attribute(database, "AI-Engines") if settings.folder_use_ai_engines else None
    types_attribute = ensure_attribute(database, "AI-Types") if settings.folder_use_ai_types else None
    genres_attribute = ensure_attribute(database, "AI-Genres") if settings.folder_use_ai_genres else None

    attributes = [engines_attribute, types_attribute, genres_attribute]

    selected_folders = ctx.selected_folders
    if len(selected_folders) == 0:
        selected_folders = [ctx.path]

    ctx.run_async(
        tag_folders, ctx.workspace_id,
        selected_folders, database, attributes)


if __name__ == "__main__":
    main()
