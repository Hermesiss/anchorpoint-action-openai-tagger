# AI Tagger for Anchorpoint

This project is an AI-based asset tagging tool for Anchorpoint

It uses OpenAI's GPT-4o model to automatically generate tags for assets based on their preview
and for folders based on the hierarchy of their contents.

## Installation

- Open `Workspace Settings`
- Open `Actions` tab
- Press `Import` button
- Paste `https://github.com/Hermesiss/anchorpoint-action-openai-tagger` into the `Repository URL` field
- Press `Connect repository` button

## Configuration

You need to provide your OpenAI API key in the Action settings.

Obtain one from [OpenAI](https://platform.openai.com/account/api-keys)

You need at least $10 in your account to use the API.

- Open Workspace Settings -> Actions -> Ai Folder and File Tools -> Settings
- Paste your API key into the `OpenAI API Key` field
- Press `Apply`

## Usage

### Tagging folders

This action will automatically tag folders based on the hierarchy of their contents and
create 3 attributes: `AI-Engines`, `AI-Types` and `AI-Genres`.

- Change to the List View (Ctrl+2)
- Select one or more folders
- Right-click on any of the selected folders
- Select `Tag Folders with AI`
- Wait for the preparation stage to finish
- You will be prompted with **token count** and **cost estimation** and a confirmation dialog
- If you confirm, the action will start, and you will be notified when it finishes

### Tagging assets

This action will automatically tag assets based on their preview and create 3 attributes: `AI-Types`, `AI-Genres` and
`AI-Objects`.

- Change to the List View (Ctrl+2)
- Select one or more assets - images, models, materials. All that have a preview
- Right-click on any of the selected assets
- Select `Tag Files with AI`
- Wait for the preparation stage to finish - generating previews and optimizing them to reduce the token count
- You will be prompted with **token count** and **cost estimation** and a confirmation dialog
- If you confirm, the action will start, and you will be notified when it finishes