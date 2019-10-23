import pyodbc
import csv
import argparse
import os

class Error(Exception):
    """Base class for exceptions"""
    pass

class ArgumentError(Error):
    """ Exception for missing arguments """
    def __init__(self, message):
        self.message = message

class MySQLInsertionException(Error):
    """ Exception for errors inserting into SQL databaase """
    def __init__(self, message):
        self.message = message

""" Class handles the arguments, and stores them for future use """
class arguments:
    def __init__(self):
        self.ARG_F = None
        self.ARG_M = None

    def parseargs(self):
        argparser = argparse.ArgumentParser(description="This script imports the data into the database for analysis")
        argparser.add_argument("--f", default=None, help="Specifies the file to import")
        argparser.add_argument("--m", default=None, help="Specifies the type of file. If not specified, then attempts to get from extension")

        #Now lets check the arguments
        args = argparser.parse_args()

        if args.f == None:
            raise ArgumentError("File was not specified, please try again")
        else:
            self.ARG_F = args.f

        """
        if args.m == None:
            raise ArgumentError("Method was not specified, please try again")
        else:
            self.ARG_M = args.m
        """


""" Create a 'database' class to handle all the interactions with the database """
class database:
    def __init__ (self):
        self.database_conn = self.connect()
        self.import_id = 0

    def connect(self):
        try:
            server = "feedback-hub.database.windows.net"
            username = "development"
            password = "jd*nc&cmFhQ1£dfg"
            database = "FeedbackHub"
            driver= '{ODBC Driver 17 for SQL Server}'

            conn = pyodbc.connect('DRIVER='+driver+';SERVER='+server+';PORT=1433;DATABASE='+database+';UID='+username+';PWD='+ password)

            return conn
        except pyodbc.Error as e:
            print("Could not connect to the database\nMessage: {}".format(e))
            exit(1)

    def createImport(self):
        cursor = self.database_conn.cursor()
        cursor.execute("INSERT INTO feedback_hub.import (import_method) VALUES('csv')")

        cursor.execute("SELECT CAST(@@IDENTITY AS INT)")
        row = cursor.fetchone()

        self.import_id = row[0]

    def addResponses(self, data):
        cursor = self.database_conn.cursor()
        rows = len(data)
        counter = 1

        for response in data:
            print("Processing response {} / {}".format(counter, rows))

            #Let us create a new response, before importing the data
            cursor.execute("INSERT INTO feedback_hub.response (import_id) VALUES(?)", str(self.import_id))

            cursor.execute("SELECT CAST (@@IDENTITY AS INT)")
            row = cursor.fetchone()
            response_id = row[0]

            #Now we loop through the data, and add each entity to the database
            for entity in response:
                cursor.execute("INSERT INTO feedback_hub.entity (response_id, raw_data) VALUES(?, ?)", str(response_id), entity)

            counter = counter + 1
        
        print("Commiting data to database")
        self.database_conn.commit() #Also can act as a transaction

class parseData:
    def csv(self, csv_filename):
        try:
            file_location = os.path.realpath(csv_filename)

            #open the file
            with open(file_location, 'r') as csv_file:
                csv_reader = csv.reader(csv_file)
                line = 0
                responses = []

                #save each row, which is one single response
                for row in csv_reader:
                    responses.append(row)
                    line = line + 1
                
                return responses 
        except UnicodeDecodeError as e:
            print("An error occured during parsing the CSV file.\nMessage: {}".format(e))
            exit(1)

# Parse arguments
args = arguments()
args.parseargs()

# Now lets get the data
data = parseData()
csv_data = data.csv(args.ARG_F)

# Finally, import into the database
db = database()
db.createImport()
db.addResponses(csv_data)

print("Data was added successfully")