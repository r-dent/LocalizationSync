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

import urllib.request
import json
import os
import re
import xml.etree.ElementTree as xml
from xml.dom import minidom

placeholderPattern = re.compile(r'{String([0-9]*)}|{Number([0-9]*)}')
scriptRunPath = os.getcwd()
scriptFileName = os.path.basename(__file__)
configFileName = os.path.splitext(scriptFileName)[0] + ".config.json"

l10nCommentIdentifier = "//"
l10nSectionTitleIdentifier = "// -"
l10nLineFormat = "\"%s\" = \"%s\";\n"

def parseDocument(spreadsheedId, sheetIndex):
    sheetUrl = "https://spreadsheets.google.com/feeds/cells/"+ spreadsheedId +"/"+ str(sheetIndex) +"/public/full?alt=json"
    
    print("Loading JSON from %s." % sheetUrl)

    with urllib.request.urlopen(sheetUrl) as response:
        content = response.read()
        parsed_json = json.loads(content)

        entries = parsed_json['feed']['entry']
        rows = {}

        for entry in entries:
            cellInfo = entry['gs$cell']
            row = int(cellInfo['row'])
            rows[row] = {}

        print("Found %i rows." % (len(rows) - 1))
        # print(json.dumps(rows, indent=4, sort_keys=True))

        for entry in entries:
            cellInfo = entry['gs$cell']
            row = int(cellInfo['row'])
            col = int(cellInfo['col'])
            cellContent = entry['content']['$t']
            rows[row][col] = cellContent

        return rows

def writeLocalizations(rows, configuration):
    languageCount = max(rows[1].keys()) - 1
    print("Found %i languages." % languageCount)

    for languageColumn in range(2, 2 + languageCount):
        languageKey = rows[1][languageColumn].replace(" ", "")
        
        if configuration["os"] == "iOS":
            buildLocalizationIOS(rows, languageColumn, languageKey, configuration)
    
        if configuration["os"] == "Android":
            buildLocalizationAndroid(rows, languageColumn, languageKey, configuration)

def buildLocalizationIOS(rows, column, languageKey, configuration):

    # Prepare paths.
    baseLanguage = "en" if (configuration["baseLanguage"] is None) else configuration["baseLanguage"]
    languageFolderName = "Base" if (languageKey == baseLanguage) else languageKey
    folderPath = configuration["outputFolder"] + "/" + languageFolderName + ".lproj"
    fileName = configuration["fileName"] + ".strings"
    filePath = folderPath + "/" + fileName

    # Prepare file.
    outputFile = startFile(folderPath, filePath, fileName)
    l10nWriteHeaderComment(fileName, outputFile)

    for row in rows:
        # Skip first row and rows without first column.
        if row == 1 or 1 not in rows[row]:
            continue

        key = rows[row][1]
        # Add section comment.
        if key.startswith(l10nSectionTitleIdentifier):
            l10nWriteSectionComment(key, outputFile)
            continue

        # Skip empty translations...
        if column not in rows[row]:
            # ...but check if the key is a commetn first.
            if key.startswith(l10nCommentIdentifier):
                l10nWriteComment(key, outputFile)
            continue

        translation = placeholderPattern.sub("%@", rows[row][column])
        line = "\"%s\" = \"%s\";" % (key, translation)
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
    isBaseLanguage = (configuration["baseLanguage"] == languageKey)
    languageFolderName = "values" if isBaseLanguage else "values-" + languageKey
    folderPath = configuration["outputFolder"] + "/" + languageFolderName
    fileName = configuration["fileName"] + ".xml"
    filePath = folderPath + "/" + fileName

    strings = []

    for row in rows:
        # Skip first row and rows without first column.
        if row == 1 or 1 not in rows[row]:
            continue

        key = rows[row][1]
        if key.startswith(l10nSectionTitleIdentifier):
            strings.append({key: ""})
            continue
        # Skip comments.
        if key.startswith(l10nCommentIdentifier):
            continue
        strings.append({key: placeholderPattern.sub("%s", rows[row][column])})

    outputFile = startFile(folderPath, filePath, fileName)
    outputFile.write(buildResourceXML(strings, "string"))
    outputFile.close()
    print("Generated " + filePath + ".")

def writeColors(rows, configuration):

    isAndroid = (configuration["os"] == "Android")
    fileExtension = ".xml" if isAndroid else ".json"
    folderPath = configuration["outputFolder"]
    fileName = configuration["fileName"] + fileExtension
    filePath = folderPath + "/" + fileName

    colors = []

    for row in rows:
        # Skip first row and rows without first column.
        if row == 1 or 1 not in rows[row]:
            continue

        key = rows[row][1]
        hexValue = rows[row][2]
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

    sheetId = config["sheetId"]

    for l10nConfig in config["l10n"]:
        tableData = parseDocument(sheetId, l10nConfig["sheetNumber"])
        writeLocalizations(tableData, l10nConfig)

    for colorConfig in config["colors"]:
        tableData = parseDocument(sheetId, colorConfig["sheetNumber"])
        writeColors(tableData, colorConfig)

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
