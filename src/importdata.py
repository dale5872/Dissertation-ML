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

    def setImportID(self, importID):
        self.import_id = importID

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
    
    def getResponseHeaders(self, questionnaireID):
        cursor = self.database_conn.cursor()
        cursor.execute("SELECT qh.header_ID \
        FROM feedbackhub.questionnaire_headers AS qh \
        WHERE qh.questionnaire_ID = {}".format(questionnaireID))

        rows = cursor.fetchall()
        headers = []

        for header in rows:
            headers.append(header[0])

        return headers

    def createImport(self, userID, originalFilename, questionnaireID):
        print("Creating Import")
        cursor = self.database_conn.cursor()
        cursor.execute("INSERT INTO feedbackhub.import (import_method, user_ID, status, filename, questionnaire_ID) VALUES('csv', ?, 'Importing', ?, ?)", userID, originalFilename, questionnaireID)

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

    def addResponses(self, data, questionnaireID):
        headers = self.getResponseHeaders(questionnaireID)
        print(headers)

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
            entity_counter = 0
            for entity in response:
                cursor.execute("INSERT INTO feedbackhub.entity (response_id, raw_data, questionnaire_header_ID) VALUES(?, ?, ?)", str(response_id), entity, headers[entity_counter])
                entity_counter = entity_counter + 1

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

    def singleResponse(self, data):
        try:
            print(data)
            csv_reader = csv.reader([data], delimiter=',')
            responses = []

            for row in csv_reader:
                responses.append(row)
            
            print(responses)
            return responses
        except UnicodeDecodeError as e:
            print("An error occured during parsing the CSV file.\nMessage: {}".format(e))
            exit(1)

def initImporter(file, originalFilename, userID, questionnaireID):        
    # Now lets get the data
    data = parseData()
    csv_data = data.csv(file)

    # Finally, import into the database
    db = database()
    db.createImport(userID, originalFilename, questionnaireID)
    responseNo = db.addResponses(csv_data, questionnaireID)
    db.finishImport(responseNo)

    print("Data was added successfully")

    return db.import_id

def insertSingleResponse(raw_data, questionnaireID, importID):
    data = parseData()
    csv_data = data.singleResponse(raw_data)

    db = database()
    db.setImportID(importID)
    db.addResponses(csv_data, questionnaireID)

    print("Response added successfully")
