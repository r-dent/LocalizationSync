#!/usr/bin/python

# Copyright (c) 2019 Roman Gille, http://romangille.com

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


from array import array
import enum
import json
import os
import re
import xml.etree.ElementTree as xml
from xml.dom import minidom

def link(uri, label=None):
    if label is None: 
        label = uri
    parameters = ''
    escape_mask = '\033]8;{};{}\033\\{}\033]8;;\033\\'
    return escape_mask.format(parameters, uri, label)

try:
    from pathlib import Path
    import shutil
    import urllib.request
except ImportError:
    print("Cannot import all modules. Are you running at least Python 3.6?")
    exit()

try:
    from pyexcel_ods import get_data as load_ods
except ImportError:
    print("Could not import "+ link("https://pypi.org/project/pyexcel-ods/", "pyexcel-ods") +".\nPlease run: pip install pyexcel-ods")
    exit()

CONF_L10N = "l10n"
CONF_COLORS = "colors"
CONF_SHEET_ID = "sheetId"
CONF_OS = "os"
CONF_SHEET_NAME = "sheetName"
CONF_BASE_LANG = "baseLanguage"
CONF_OUT_FOLDER = "outputFolder"
CONF_FILE_NAME = "fileName"
CONF_KEY_PREFIX = "keyPrefix"
CONF_KEY_ROW = "keyRow"
CONF_KEY_COL = "keyColumn"

placeholderPattern = re.compile(r'{String([0-9]*)}|{Number([0-9]*)}')
scriptRunPath = os.getcwd()
scriptFileName = os.path.basename(__file__)
configFileName = os.path.splitext(scriptFileName)[0] + ".config.json"
exportedFilesFolder = scriptRunPath + "/tmp"

l10nCommentIdentifier = "//"
l10nSectionTitleIdentifier = "// -"
l10nLineFormat = "\"%s\" = \"%s\";\n"

def loadDocument(spreadsheedId):
    tempPath = Path('tmp')
    if tempPath.exists() and tempPath.is_dir():
        shutil.rmtree(tempPath)
    os.makedirs(tempPath, exist_ok=True)
    exportUrl = "https://docs.google.com/spreadsheets/d/"+ spreadsheedId +"/export?format=ods&id="+ spreadsheedId
    localFilename = exportedFilesFolder +"/sheet_"+ spreadsheedId +"_exported.ods"
    
    print("Loading "+ link(exportUrl))
    print("Creating temp file "+ localFilename)

    urllib.request.urlretrieve(exportUrl, localFilename)
    content = load_ods(localFilename)

    shutil.rmtree(tempPath)
    return content

# TRims stuff
def trim(rows: list, firstRow: int, firstColumn: int) -> list:
    trimmedRows = []
    for rowIndex, row in enumerate(rows):
        if rowIndex < firstRow:
            continue
        trimmedRow = []
        for colIndex, col in enumerate(row):
            if colIndex < firstColumn:
                continue
            trimmedRow.append(col)
        trimmedRows.append(trimmedRow)
    return trimmedRows

def writeLocalizations(document: dict, configuration: dict):
    # Set default values.
    if (CONF_BASE_LANG not in configuration): configuration[CONF_BASE_LANG] = "en"
    if (CONF_KEY_PREFIX not in configuration): configuration[CONF_KEY_PREFIX] = ""
    keyRow: int = 0 if (CONF_KEY_ROW not in configuration) else int(configuration[CONF_KEY_ROW])
    keyColumn: int = 0 if (CONF_KEY_COL not in configuration) else int(configuration[CONF_KEY_COL])

    rows = trim(
        rows=document[configuration[CONF_SHEET_NAME]], 
        firstRow=keyRow, 
        firstColumn=keyColumn
    )
    languageCount = len(rows[0]) - 1
    print("Found %i languages." % languageCount)

    for languageColumn in range(1, 1 + languageCount):
        languageKey = rows[0][languageColumn].strip().lower()
        if " " in languageKey:
            print("\""+ languageKey +"\" is not a valid language key. Skipped processing. Please check your config!")
            continue
        print("Processing \""+ languageKey +"\" at column "+ str(languageColumn + keyColumn) +".")
        
        if configuration["os"] == "iOS":
            buildLocalizationIOS(rows, languageColumn, languageKey, configuration)
    
        if configuration["os"] == "Android":
            buildLocalizationAndroid(rows, languageColumn, languageKey, configuration)

def buildLocalizationIOS(rows, column, languageKey, configuration):

    # Prepare paths.
    languageFolderName = "Base" if (languageKey == configuration[CONF_BASE_LANG]) else languageKey
    folderPath = configuration[CONF_OUT_FOLDER] + "/" + languageFolderName + ".lproj"
    fileName = configuration[CONF_FILE_NAME] + ".strings"
    filePath = folderPath + "/" + fileName

    # Prepare file.
    outputFile = startFile(folderPath, filePath, fileName)
    l10nWriteHeaderComment(fileName, outputFile)

    for index, row in enumerate(rows):
        # Skip first row and rows without first column.
        if index == 0 or not row or not row[0]:
            continue
        key = row[0]

        # Add section comment.
        if key.startswith(l10nSectionTitleIdentifier):
            l10nWriteSectionComment(key, outputFile)
            continue

        # Skip empty translations...
        if not (column < len(row)) or (not row[column]):
            continue

        translation = placeholderPattern.sub("%@", row[column])
        line = "\"%s\" = \"%s\";" % (configuration[CONF_KEY_PREFIX] + key, translation)
        # Check if the line is commented.
        if key.startswith(l10nCommentIdentifier):
            l10nWriteComment(line, outputFile)
            continue

        # Write line.
        outputFile.write("%s\n" % line)

    outputFile.close()
    print("Generated " + filePath + ".")

def buildLocalizationAndroid(rows, column, languageKey, configuration):

    # Prepare paths.
    isBaseLanguage = (configuration[CONF_BASE_LANG] == languageKey)
    languageFolderName = "values" if isBaseLanguage else "values-" + languageKey
    folderPath = configuration[CONF_OUT_FOLDER] + "/" + languageFolderName
    fileName = configuration[CONF_FILE_NAME] + ".xml"
    filePath = folderPath + "/" + fileName

    strings = []

    for index, row in enumerate(rows):
        # Skip first row and rows without first column.
        if index == 0 or not row or not row[0]:
            continue
        key = row[0]

        if key.startswith(l10nSectionTitleIdentifier):
            strings.append({key: ""})
            continue

        # Skip empty translations...
        if not (column < len(row)) or (not row[column]):
            continue
        
        # Skip comments.
        if key.startswith(l10nCommentIdentifier):
            continue
        strings.append({configuration[CONF_KEY_PREFIX] + key: placeholderPattern.sub("%s", row[column])})

    outputFile = startFile(folderPath, filePath, fileName)
    outputFile.write(buildResourceXML(strings, "string"))
    outputFile.close()
    print("Generated " + filePath + ".")

def writeColors(document, configuration):

    rows = document[configuration[CONF_SHEET_NAME]]
    isAndroid = (configuration["os"] == "Android")
    fileExtension = ".xml" if isAndroid else ".json"
    folderPath = configuration[CONF_OUT_FOLDER]
    fileName = configuration[CONF_FILE_NAME] + fileExtension
    filePath = folderPath + "/" + fileName

    colors = []

    for index, row in enumerate(rows):
        # Skip first row and rows without first column.
        if index == 0 or not row or not row[0]:
            continue
        key = row[0]
        hexValue = row[1]
        colors.append({key: hexValue})

    outputFile = startFile(folderPath, filePath, fileName)

    if isAndroid:
        outputFile.write(buildResourceXML(colors, "color"))
    else:
        jsonDict = {}
        for item in colors:
            key = next(iter(item))
            jsonDict[key] = item[key]
        json.dump(jsonDict, outputFile)
    

    outputFile.close()
    print("Generated " + filePath + ".")

def buildResourceXML(keyValueArray, elementName):
    root = xml.Element("resources")
    root.insert(0, xml.Comment("Generated with " + scriptFileName))
    itemCount = 0

    for item in keyValueArray:
        key = next(iter(item))
        if key.startswith(l10nSectionTitleIdentifier):
            # Add comment.
            root.insert(itemCount, xml.Comment(xmlWriteSectionComment(key)))
            continue
        # Add line.
        xml.SubElement(root, elementName, name=key).text = item[key]
        itemCount += 1

    xmlString = xml.tostring(root)
    return minidom.parseString(xmlString).toprettyxml()

def startFile(folderPath, filePath, fileName, binary=False):

    os.makedirs(folderPath, exist_ok=True)
    fileHandler = open(filePath, "wb" if (binary) else "w")
    return fileHandler

# Comment helper.

def l10nWriteComment(comment, fileHandler):

    fileHandler.write("/* %s */\n" % comment.replace(l10nCommentIdentifier, ""))

def l10nWriteHeaderComment(fileName, fileHandler):

    fileHandler.write("/*\n  " + fileName + "\n  Generated with " + scriptFileName + ".\n*/\n\n")

def l10nWriteSectionComment(sectionTitle, fileHandler):

    fileHandler.write("\n/*\n Section: %s\n*/\n" % sectionTitle.replace(l10nSectionTitleIdentifier, "").replace(" ", ""))

def xmlWriteSectionComment(sectionTitle):

    return "Section: %s" % sectionTitle.replace(l10nSectionTitleIdentifier, "").replace(" ", "")

# Run.

def run(config):

    sheetId = config[CONF_SHEET_ID]
    try:
        document = loadDocument(sheetId)

        if CONF_L10N in config:
            for l10nConfig in config[CONF_L10N]:
                writeLocalizations(document, l10nConfig)

        if CONF_COLORS in config:
            for colorConfig in config[CONF_COLORS]:
                writeColors(document, colorConfig)

    except Exception as exc:
        print("Cannot process sheet - Error:")
        print(exc)

def main():
    # Parse config file and run tasks.
    try:
        with open(configFileName, 'r') as stream:
            config = json.load(stream)
            run(config)

    except json.JSONDecodeError as exc:
        print("Error parsing config file: ")
        print(exc)

    except FileNotFoundError:
        print("Error: Could not find \"" + configFileName + "\". This should be placed at the run directory of this script. Current run directory is \"" + scriptRunPath +"\".")

# This will get called when the file is called via `python fileneme.py`
if __name__ == '__main__':
    main()
