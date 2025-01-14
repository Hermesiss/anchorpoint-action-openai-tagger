import os
import typing

import anchorpoint as ap
import apsync as aps


class CreateTagFilesDialogData:
    def __init__(
            self, input_paths: list[str], total_tokens: int, combined_output_tokens: int, pixel_count: int,
            total_price: float):
        self.input_paths = input_paths
        self.total_tokens = total_tokens
        self.combined_output_tokens = combined_output_tokens
        self.pixel_count = pixel_count
        self.total_price = total_price


def create_tag_files_dialog(data: CreateTagFilesDialogData,
                            callback: typing.Callable[[ap.Dialog], None]) -> ap.Dialog:
    proceed_dialog = ap.Dialog()
    proceed_dialog.title = "Estimated Costs"
    ctx = ap.get_context()
    proceed_dialog.icon = ctx.icon
    proceed_dialog.add_text(f"Processing files: {len(data.input_paths)}"
                            f"\nInput token count: {data.total_tokens}"
                            f"\nOutput token count: ~{data.combined_output_tokens}"
                            f"\nPixel count: {data.pixel_count}"
                            f"\nCosts: ~${round(data.total_price,6)}")
    proceed_dialog.add_empty()
    proceed_dialog.add_checkbox(True, None, var="skip_existing_tags",text="Skip existing tags")
    (
        proceed_dialog
        .add_button("Continue", callback=callback)
        .add_button("Cancel", callback=lambda d: d.close(), primary=False)
    )
    return proceed_dialog


class CreateTagFoldersDialogData:
    def __init__(self, folders: list[tuple[str, str, int, float]], output_token_count: int, output_token_price: float):
        self.folders = folders
        self.output_token_count = output_token_count
        self.output_token_price = output_token_price


def create_tag_folders_dialog(data: CreateTagFoldersDialogData,
                              callback: typing.Callable[[ap.Dialog], None]) -> ap.Dialog:
    proceed_dialog = ap.Dialog()
    proceed_dialog.title = "Estimated Costs"    
    ctx = ap.get_context()
    proceed_dialog.icon = ctx.icon
    combined_tokens = sum([folder[2] for folder in data.folders])
    combined_output_tokens = len(data.folders) * data.output_token_count
    combined_input_price = sum([folder[3] for folder in data.folders])
    combined_output_price = combined_output_tokens * data.output_token_price
    proceed_dialog.add_text(f"Input token count: {combined_tokens}"
                            f"\nOutput token count: ~{combined_output_tokens}"
                            f"\nCosts: ~${round((combined_input_price + combined_output_price),6)}")
    (
        proceed_dialog
        .add_button("Continue", callback=callback)
        .add_button("Cancel", callback=lambda d: d.close(), primary=False)
    )

    return proceed_dialog
