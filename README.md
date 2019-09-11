# Localization Sync
...and other things.

This is a python script that downloads localization strings and CI color information from a public [Google Sheet](https://docs.google.com/spreadsheets) and generates resource files for iOS and Android for use in App projects.

![Vizualization of the workflow](Resources/workflow.jpg)

## Usage

Create a Google Sheet document with sheets like these:

![Example of a L10n table](Resources/sheet_l10n.png)
![Example of a colors table](Resources/sheet_colors.png)

Publish the sheeet to the web by pressing __File -> Publish to the web__. Select __Whole Document__ and __Website__. This gives the script access to the public JSON API of Google Docs.

Find the ID of your document by copying it from your browsers address bar.

![sheet_url.png](Resources/sheet_url.png)

__--> TODO: Setting up the script Section__

## Example

Go to your terminal of choice and run

```bash
python3 Sources/data_sync.py
```