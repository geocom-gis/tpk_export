#-------------------------------------------------------------------------------
# Name:        tpk_export.py
# Purpose:     Find all the map documents that reside in a specified folder and
#              create tile packages for each map document.
#
# Author:      Geocom Informatik AG
#
# Created:     07.11.2018
# Copyright:   (c) Geocom Informatik AG 2018
#-------------------------------------------------------------------------------

import os
import sys
import arcpy
import datetime
import argparse
import xml.etree.cElementTree as ET

def createLogfile(logDir, logName):
    """
    Creates a logfile in the given directory with the given name.
    Needs:
        logDir:  The directory where the logfile will be stored
        logName: The Name of the log file. Nameing pattern [date]__[logName]
    """
    logFile = open(logDir + "\\" + str(datetime.date.today()) +"__" + logName, "w")
    logFile.write("Tile package export log - " + str(datetime.date.today()))
    logFile.write("\n------------------------------------\n")

    return logFile

def writeLog(logFile, exception, error_count, mxd):
    """
    Writes an error message into a logfile.
    Needs:
        logFile:     an open file
        exception:   the error message to writ into the file
        error_count: the number of error during processing
        mxd:         the name of the mxd file that caused the error
    """
    logLines = ["#################\n", "Error number: " + str(error_count) +"\n", "Caused by: " + mxd + "\n", "Message:\n" , str(exception), "\n"]
    logFile.writelines(logLines)


def closeLog(logFile, error_count):
     """
     Writes an end message into the given logfile and closes it.
     Needs:
         logFile:     an open file
         error_count: the number of errors during processing
      """
     if error_count == 0:
        print("-------")
        print("All map packages successfully created.")
        logFile.write("CONGRATULATIONS! No erros occured during processing." )
     elif error_count == 1:
        print("-------")
        print("An error occured during packaging. Refer to the logfile for detailed information.")
     elif error_count == -1:
        print("-------")
        print("There are no MXD in the given input directory!")
        logFile.write("The given input directory was empty! Thus no tpk could be exported.")
     else:
        print("-------")
        print(str(error_count) + " errors occured during packaging. Refer to the logfile for detailed information.")
     logFile.close()

def checkDirectory(path):
    """
    Checks if a directory does exist. If not, tries to create it.
    Needs:
        path: the path to be checked
    """
    if os.path.exists(path):
        if not os.path.isdir(path):
            path = raw_input("The given input refers to a file. Please provide the path only:  ")
            checkDirectory(path)
    else:
        try:
            print("The given diretory does not exist. Trying to create it:")
            os.makedirs(path)
            print("Directory successfully created!")
        except Exception as e:
            print("ERROR while creating directory. Error message: \n")
            print e

def parseScheme(logFile,scheme_path):
    """
    Parses and the level of detail out of the given tiling scheme.
    Needs:
        scheme_path: the path to the scheme file
    """
    try:
        scheme_tree = ET.parse(scheme_path)
        scheme_root = scheme_tree.getroot()


        # get the last element with tag "LODInfo"
        lod_info = scheme_root.findall('.//LODInfos/LODInfo/[last()]')[0]
        # read the actual level of detail and add 1 (since LevelID starts with 0)
        lod = int(lod_info.find('LevelID').text) + 1
    except Exception as e:
        writeLog(logFile, e, 1, "The file " + scheme_path + " is not a valid scheme file!")
        lod = None
    return lod

def exportTpk(arguments):
    """
    Goes through the list of mxds in the given directory and tries to export them as tpks.
    Tries to find a scheme file and the lod value if none are given in arguments.
    Needs:
        arguments: the list of arguments from the parser in main()
    """
    workspace = arguments.inDir
    output = arguments.outDir
    logDir = arguments.logDir
    logName = arguments.logName
    scheme_name = arguments.schemeName
    error_count = 0
    #Set environment settings
    arcpy.env.overwriteOutput = True
    arcpy.env.workspace = workspace
    mxdlist = arcpy.ListFiles("*.mxd")

    #creat a log file
    log = createLogfile(logDir, logName)

    # if no scheme was given try the first .xml in the directory
    if scheme_name == None:
        xmls = arcpy.ListFiles("*.xml")
        if len(xmls) > 0:
            scheme_name = xmls[0]
            scheme_path = workspace + '\\' + scheme_name
        else:
            error_count = 1
            message = ("There is no scheme file in the directory!")
            writeLog(log, message, error_count, "No scheme file available")
    else:
        scheme_path = workspace + '\\' + scheme_name
    # if no lod is given, parse it from the scheme
    if error_count == 0:
        if arguments.detailLevel == None:
            lod = parseScheme(log, scheme_path)
            # If there was no result, increase error_count
            if lod == None:
                error_count = 1
        else:
            lod = arguments.detailLevel

    # Loop through the workspace, find all the mxds and create a tile package using the same name as the mxd
    if error_count == 0:
        if len(mxdlist)< 1:
            error_count -= 1
        else:
            # Loop through the workspace, find all the mxds and create a tile package using the same name as the mxd
            for mxd in mxdlist:
                print("Packaging " + mxd)
                outPath = output + "\\" + os.path.splitext(mxd)[0]
                # set summary if none was given
                if arguments.summary == None:
                    summary = os.path.splitext(mxd)[0]
                else:
                    summary = arguments.summary
                # set a tag if none was given
                if arguments.tags == None:
                    tags = os.path.splitext(mxd)[0]
                else:
                    tags = arguments.tags
                # try to create tile packeage
                try:
                    arcpy.CreateMapTilePackage_management(mxd, "EXISTING", outPath + '.tpk',
                    arguments.format, lod, scheme_path, summary, tags)
                    print("SUCCESS: " + mxd + " processed successfully.")
                    # if a packaging folder was created, it will be removed
                    if os.path.exists(outPath):
                        try:
                            shutil.rmtree(outPath, onerror=remove_readonly)
                        except Exception as e:
                            error_count += 1
                            writeLog(log, e, error_count, mxd)
                            print("Removal of package directory " + outPath + " failed. Consider running the script with administrator permissions.")
                except Exception as e:
                    error_count += 1
                    writeLog(log, e, error_count, mxd)
                    print("ERROR while processing " + mxd)

    # close the Logfile
    closeLog(log, error_count)

def main():
    """
    Defines and parses the arguments of the given module. Invokes tpkExport.
    """
    parser = argparse.ArgumentParser(description="TPK export tool V1.0")
    parser.add_argument("-s", "--silent", help="Use to prevent user interaction. If no paths are given (see -i, -o, -l), the path of this script will be used for either path. Everything else will run on default values. You still need to provide a scheme file though! ", action="store_true")
    parser.add_argument("-i", "--inDir", metavar="", type=str, help="The directory where the mxds are stored. Asks for user interaction if not set.", default=None)
    parser.add_argument("-o", "--outDir", metavar="", type=str, help="The directory where the tpks will be exported to. Asks for user interaction if not set.",default=None)
    parser.add_argument("-l", "--logDir", metavar="", type=str, help="The directory where the logfile will be created. Asks for user interaction if not set.",default=None)
    parser.add_argument("-ln", "--logName", metavar="", type=str, help="The name of the logfile (default: [date]__tpk_export.log)",default="tpk_export.log")
    parser.add_argument("-f", "--format", metavar="", choices=["PNG", "PNG8", "PNG16", "PNG24", "PNG32", "JPG", "MIXED"], action="store", dest="format", type=str, help="The format of the tiles (default: PNG)", default="PNG")
    parser.add_argument("-dl", "--detailLevel", metavar="", type=int, help="The level of detail. If not set it will be parsed from the scheme file.")
    parser.add_argument("-sc", "--schemeName", metavar="", type=str, help="The name of the scheme file to be applied (including file ending). It is considered to be in the input directory (see -i). Asks for user interaction if not set.", default=None)
    parser.add_argument("-sum", "--summary", metavar="", type=str, help="Summary text to be added to the TPK. If not set the name of the mxd will be used.")
    parser.add_argument("-t", "--tags", metavar="", type=str, help="The tags to be added to the TPK (comma separated). If not set the name of the mxd will be used.")

    arguments = parser.parse_args()
    if arguments.silent:
        if arguments.inDir == None:
            arguments.inDir = sys.path[0]
        if arguments.outDir == None:
            arguments.outDir = sys.path[0]
        if arguments.logDir == None:
            arguments.logDir = sys.path[0]
        if arguments.schemeName == None:
            print("ERROR: No tiling scheme was provided. Aborting export. Type 'tpk_export.py -h' for help. ")
            exit()
    else:
        if arguments.inDir == None:
            arguments.inDir = raw_input("Enter input folder: ")
            checkDirectory(arguments.inDir)
        if arguments.outDir == None:
            arguments.outDir = raw_input("Enter destination folder for .tpk: ")
            checkDirectory(arguments.outDir)
        if arguments.logDir == None:
            arguments.logDir = raw_input("Enter folder for logfiles: ")
            checkDirectory(arguments.outDir)
        if arguments.schemeName == None:
            arguments.schemeName = raw_input("Enter the name of the scheme file (without path):")

    exportTpk(arguments)

main()