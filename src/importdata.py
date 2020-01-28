import pyodbc
import csv
import os

class Error(Exception):
    """Base class for exceptions"""
    pass


class MySQLInsertionException(Error):
    """ Exception for errors inserting into SQL databaase """
    def __init__(self, message):
        self.message = message


""" Create a 'database' class to handle all the interactions with the database """
class database:
    def __init__ (self):
        self.database_conn = self.connect()
        self.import_id = 0

    def connect(self):
        try:
            server = "feedback-hub.database.windows.net"
            username = "dale"
            password = "[REDACTED]"
            database = "FeedbackHub"
            driver= '{ODBC Driver 17 for SQL Server}'

            conn = pyodbc.connect('DRIVER='+driver+';SERVER='+server+';PORT=1433;DATABASE='+database+';UID='+username+';PWD='+ password)

            return conn
        except pyodbc.Error as e:
            print("Could not connect to the database\nMessage: {}".format(e))
            exit(1)

    def createImport(self, userID, originalFilename):
        print("Creating Import")
        cursor = self.database_conn.cursor()
        cursor.execute("INSERT INTO feedbackhub.import (import_method, user_ID, status, filename) VALUES('csv', ?, 'Importing', ?)", userID, originalFilename)

        cursor.execute("SELECT CAST(@@IDENTITY AS INT)")
        row = cursor.fetchone()

        self.import_id = row[0]
        
        print("Commiting import to database")
        self.database_conn.commit()

    def finishImport(self, responses):
        print("Updating Database")

        cursor = self.database_conn.cursor()
        cursor.execute("UPDATE feedbackhub.import SET status = 'Complete', responses = ? WHERE import_ID = ?", responses, self.import_id)

        print("Commiting import complete to database")
        self.database_conn.commit()

    def addResponses(self, data):
        cursor = self.database_conn.cursor()
        rows = len(data)
        counter = 1

        for response in data:
            print("Processing response {} / {}".format(counter, rows))

            #Let us create a new response, before importing the data
            cursor.execute("INSERT INTO feedbackhub.response (import_id) VALUES(?)", str(self.import_id))

            cursor.execute("SELECT CAST (@@IDENTITY AS INT)")
            row = cursor.fetchone()
            response_id = row[0]

            #Now we loop through the data, and add each entity to the database
            for entity in response:
                cursor.execute("INSERT INTO feedbackhub.entity (response_id, raw_data) VALUES(?, ?)", str(response_id), entity)

            counter = counter + 1
        
        print("Commiting data to database")
        self.database_conn.commit() #Also can act as a transaction

        return counter

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

def initImporter(file, originalFilename, userID):        
    # Now lets get the data
    data = parseData()
    csv_data = data.csv(file)

    # Finally, import into the database
    db = database()
    db.createImport(userID, originalFilename)
    responseNo = db.addResponses(csv_data)
    db.finishImport(responseNo)

    print("Data was added successfully")

    return db.import_id