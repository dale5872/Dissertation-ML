import importdata
import analyse
import argparse

class Error(Exception):
    """Base class for exceptions"""
    pass

class ArgumentError(Error):
    """ Exception for missing arguments """
    def __init__(self, message):
        self.message = message

""" Class handles the arguments, and stores them for future use """
class arguments:
    def __init__(self):
        self.ARG_F = None #Filename
        self.ARG_M = None #Method
        self.ARG_U = None #UserID
        self.ARG_O = None #Original Filename, as reuploaded

    def parseargs(self):
        argparser = argparse.ArgumentParser(description="This script imports the data into the database for analysis")
        argparser.add_argument("--f", default=None, help="Specifies the file to import")
        argparser.add_argument("--m", default=None, help="Specifies the type of file. If not specified, then attempts to get from extension")
        argparser.add_argument("--u", default=None, help="Specifies the UserID of the importer")
        argparser.add_argument("--o", default=None, help="Specifies the original filename, as this is renamed when uploaded")

        #Now lets check the arguments
        args = argparser.parse_args()

        if args.f == None:
            raise ArgumentError("File was not specified, please try again")
        else:
            self.ARG_F = args.f

        if args.u == None:
            raise ArgumentError("UserID was not specified. Please specify a UserID")
        else:
            self.ARG_U = args.u

        if args.o == None:
            raise ArgumentError("Original filename was not specified")
        else:
            self.ARG_O = args.o

        """
        if args.m == None:
            raise ArgumentError("Method was not specified, please try again")
        else:
            self.ARG_M = args.m
        """

# Parse arguments
args = arguments()
args.parseargs()

importID = importdata.initImporter(args.ARG_F, args.ARG_O, args.ARG_U)
analyse.initAnalysis(importID)
