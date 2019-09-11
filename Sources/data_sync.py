#!/usr/bin/python

import urllib.request
import json
import os
import re

baseLanguage = "en"
projectFolder = "RapScript"
placeholderPattern = re.compile(r'{String([0-9]*)}|{Number([0-9]*)}')


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

def buildLocalizationIOS(rows, column, languageKey, configuration):

    # Prepare paths.
    languageFolderName = "Base" if (languageKey == baseLanguage) else languageKey
    folderPath = configuration["projectFolder"] + "/" + languageFolderName + ".lproj"
    fileName = configuration["stringsFileName"] + ".strings"
    filePath = folderPath + "/" + fileName

    # Prepare file.
    outputFile = startFile(folderPath, filePath, fileName)
    writeHeaderComment(fileName, outputFile)

    for row in range(2, 1 + len(rows)):
        key = rows[row][1]
        if key.startswith("/"):
            writeSectionComment(key, outputFile)
            continue
        translation = placeholderPattern.sub("%@", rows[row][column])
        # Write line.
        outputFile.write("\"%s\" = \"%s\";\n" % (key, translation))

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

def startFile(folderPath, filePath, fileName):

    os.makedirs(folderPath, exist_ok=True)
    fileHandler = open(filePath, "w")
    return fileHandler

def writeHeaderComment(fileName, fileHandler):

    fileHandler.write("/*\n  " + fileName + "\n  Generated with " + os.path.basename(__file__) + ".\n*/\n\n")

def writeSectionComment(sectionTitle, fileHandler):

    fileHandler.write("\n/*\n Section: %s\n*/\n" % sectionTitle.replace("/", "").replace(" ", ""))
        


# Write Localizable.strings.
stringsTable = parseDocument("1mgbrulyTgQfSQPBLESCbPDsGBPvnX-vf_g14NbP102o", 1)
writeLocalizations(stringsTable, {
    "os": "iOS",
    "projectFolder": projectFolder,
    "stringsFileName": "Localizable"    
})

# Write InfoPlist.strings.
permissionsTable = parseDocument("1mgbrulyTgQfSQPBLESCbPDsGBPvnX-vf_g14NbP102o", 3)
writeLocalizations(permissionsTable, {
    "os": "iOS",
    "projectFolder": projectFolder,
    "stringsFileName": "InfoPlist"    
})

# Write colors.xml.
colorsTable = parseDocument("1mgbrulyTgQfSQPBLESCbPDsGBPvnX-vf_g14NbP102o", 2)
writeColors(colorsTable, {
    "os": "iOS",
    "outputFolder": projectFolder + "/Generated",
    "fileName": "colors"    
})
