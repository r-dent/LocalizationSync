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
    folderPath = configuration["projectFolder"] + "/" + languageFolderName + ".lproj"
    fileName = configuration["stringsFileName"] + ".strings"
    filePath = folderPath + "/" + fileName

    # Prepare file.
    outputFile = startFile(folderPath, filePath, fileName)
    outputFile.write("/*\n  " + fileName + "\n  Generated with " + scriptFileName + ".\n*/\n\n")

    for row in range(2, 1 + len(rows)):
        key = rows[row][1]
        if key.startswith("/"):
            outputFile.write("\n/*\n %s\n*/\n" % sectionComment(key))
            continue
        translation = placeholderPattern.sub("%@", rows[row][column])
        # Write line.
        outputFile.write("\"%s\" = \"%s\";\n" % (key, translation))

    outputFile.close()
    print("Generated " + filePath + ".")

def buildLocalizationAndroid(rows, column, languageKey, configuration):

    # Prepare paths.
    isBaseLanguage = (configuration["baseLanguage"] == languageKey)
    languageFolderName = "values" if isBaseLanguage else "values-" + languageKey
    folderPath = configuration["projectFolder"] + "/" + languageFolderName
    fileName = "strings.xml"
    filePath = folderPath + "/" + fileName

    # Start XML tree.
    root = xml.Element("resources")
    root.insert(0, xml.Comment("Generated with " + scriptFileName))
    stringsCount = 0

    for row in range(2, 1 + len(rows)):
        key = rows[row][1]
        if key.startswith("/"):
            root.insert(stringsCount, xml.Comment(sectionComment(key)))
            continue
        translation = placeholderPattern.sub("%s", rows[row][column])
        # Add line.
        xml.SubElement(root, "string", name=key).text = translation
        stringsCount += 1

    xmlString = xml.tostring(root)
    prettyXMLString = minidom.parseString(xmlString).toprettyxml()

    outputFile = startFile(folderPath, filePath, fileName)
    outputFile.write(prettyXMLString)
    outputFile.close()
    print("Generated " + filePath + ".")

def writeColors(rows, configuration):

    folderPath = configuration["outputFolder"]
    fileName = configuration["fileName"] + ".json"
    filePath = folderPath + "/" + fileName

    colors = {}

    for row in range(2, 1 + len(rows)):
        key = rows[row][1]
        hexValue = rows[row][2]
        colors[key] = hexValue

    outputFile = startFile(folderPath, filePath, fileName)
    json.dump(colors, outputFile)
    outputFile.close()
    print("Generated " + filePath + ".")

def startFile(folderPath, filePath, fileName, binary=False):

    os.makedirs(folderPath, exist_ok=True)
    fileHandler = open(filePath, "wb" if (binary) else "w")
    return fileHandler

def sectionComment(sectionTitle):

    return "Section: %s" % sectionTitle.replace("/", "").replace(" ", "")

def run(config):

    sheetId = config["sheetId"]

    for l10nConfig in config["l10n"]:
        tableData = parseDocument(sheetId, l10nConfig["sheetNumber"])
        writeLocalizations(tableData, l10nConfig)

    for colorConfig in config["colors"]:
        tableData = parseDocument(sheetId, colorConfig["sheetNumber"])
        writeColors(tableData, colorConfig)

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
