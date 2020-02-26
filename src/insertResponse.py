import importdata
import analyse
import classifier
import argparse
import traceback

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
        self.ARG_D = None #Original Filename, as reuploaded
        self.ARG_Q = None #QuestionnaireID
        self.ARG_I = None #ImportID
        self.ARG_U = None #UserID

    def parseargs(self):
        argparser = argparse.ArgumentParser(description="This script imports the data into the database for analysis")
        argparser.add_argument("--d", default=None, help="Specifies the data to insert, in csv format")
        argparser.add_argument("--q", default=None, help="Specifies the questionnaireID")
        argparser.add_argument("--i", default=None, help="Specifies the importID of the questionnaire")
        argparser.add_argument("--u", default=None, help="Specifies the UserID of the importer")


        #Now lets check the arguments
        args = argparser.parse_args()

        if args.d == None:
            raise ArgumentError("Datya was not specified")
        else:
            self.ARG_D = args.d

        if args.q == None:
            raise ArgumentError("QuestionnaireID required")
        else:
            self.ARG_Q = args.q

        if args.i == None:
            raise ArgumentError("ImportID required")
        else:
            self.ARG_I = args.i

        if args.u == None:
            raise ArgumentError("UserID was not specified. Please specify a UserID")
        else:
            self.ARG_U = args.u


        """
        if args.m == None:
            raise ArgumentError("Method was not specified, please try again")
        else:
            self.ARG_M = args.m
        """

# Parse arguments
try:
    args = arguments()
    args.parseargs()

    importdata.insertSingleResponse(args.ARG_D, args.ARG_Q, args.ARG_I)
    analyse.initAnalysis(args.ARG_I)
    classifier.initClassifier(args.ARG_I, args.ARG_U)
    exit(0)
except Exception as e:
    print(e)
    traceback.print_exec()
    exit(1)
