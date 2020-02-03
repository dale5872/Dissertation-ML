import os
import sys
import pyodbc
import pandas as pd
from sklearn.tree import DecisionTreeClassifier, export_graphviz
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.externals.six import StringIO  
from IPython.display import Image  
import pydotplus

DEBUG = True

class database:
    def __init__(self):
        self.conn = self.connect()

    def connect(self):
        global DEBUG
        try:
            server = "feedback-hub.database.windows.net"
            username = "dale"
            password = "[REDACTED]"
            database = "FeedbackHub"
            driver= '{ODBC Driver 17 for SQL Server}'

            conn = pyodbc.connect('DRIVER='+driver+';SERVER='+server+';PORT=1433;DATABASE='+database+';UID='+username+';PWD='+ password)

            if DEBUG:
                print("Connected to database")

            return conn
        except pyodbc.Error as e:
            print("Could not connect to the database\nMessage: {}".format(e))
            exit(1)

    def loadDataset(self, import_ID):
        global DEBUG

        if DEBUG:
            print("Loading Live Data")

        cursor = self.conn.cursor()
        cursor.execute("SELECT a.entity_ID, a.stopword_lexical_richness, a.grammatical_incorrectness, a.lexical_richness \
        FROM (((feedbackhub.analysis AS a \
            INNER JOIN feedbackhub.entity AS e ON a.entity_ID = e.entity_ID) \
            INNER JOIN feedbackhub.response AS r ON r.response_ID = e.response_ID) \
            INNER JOIN feedbackhub.import AS i ON i.import_ID = r.import_ID) \
        WHERE i.import_ID = {};".format(import_ID))

        rows = cursor.fetchall()

        entityID = []
        stop_word_lexical_richness = []
        grammatical_incorrectness = []
        lexical_richness = []

        for entity in rows:
            entityID.append(entity[0])
            stop_word_lexical_richness.append(entity[1])
            grammatical_incorrectness.append(entity[2])
            lexical_richness.append(entity[3])

        dataset = {
            'entityID': entityID,
            'stopword_lexical_richness': stop_word_lexical_richness,
            'grammatical_incorrectness': grammatical_incorrectness,
            'lexical_richness': lexical_richness
        }

        return pd.DataFrame(dataset)

    def loadTrainingSet(self):
        global DEBUG

        if DEBUG:
            print("Loading Training Data")

        cursor = self.conn.cursor()
        cursor.execute("SELECT convert(VARCHAR, t.stopword_lexical_richness), \
        convert(VARCHAR, t.grammatical_incorrectness), \
        convert(VARCHAR, t.lexical_richness), \
        t.classification \
        FROM feedbackhub.training_set AS T")
        rows = cursor.fetchall()

        stop_word_lexical_richness = []
        grammatical_incorrectness = []
        lexical_richness = []
        classification = []

        for response in rows:
            stop_word_lexical_richness.append(response[0])
            grammatical_incorrectness.append(response[1])
            lexical_richness.append(response[2])
            classification.append(response[3])

        training_set = {
            'stopword_lexical_richness': stop_word_lexical_richness,
            'grammatical_incorrectness': grammatical_incorrectness,
            'lexical_richness': lexical_richness,
            'classification': classification
        }

        #We now need to turn this into a dataframe and return it
        return pd.DataFrame(training_set)
    
    def insertClassification(self, entity_ID, classification):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO feedbackhub.classifications (entity_ID, classification) VALUES(?, ?)", int(entity_ID), int(classification))

        self.conn.commit()

class classifier:
    def __init__(self, training_set, dataset, database):
        self.dataset = dataset
        self.training_set = training_set
        self.classifier = None
        self.database = database

    def trainDecisionTree(self):
        global DEBUG
        if DEBUG:
            print("Creating Training Model...")

        feature_cols = ['stopword_lexical_richness', 'grammatical_incorrectness', 'lexical_richness']

        X = self.training_set.drop('classification', axis=1)
        Y = self.training_set['classification']

        """ Set the training set size to 80%, where the remaining 20% will be tested
        on the trained model """
        X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size = 0.2)

        if DEBUG:
            print("Initialising Classifier")

        self.classifier = DecisionTreeClassifier()#criterion="gini", splitter="best",max_depth=3)
        self.classifier.fit(X_train, Y_train)

        if DEBUG:
            print("Analysing Model Correctness")

        #Lets verify the model
        Y_pred = self.classifier.predict(X_test)
        print(Y_pred)

        print(confusion_matrix(Y_pred, Y_test))
        print(classification_report(Y_pred, Y_test))

        #Output decision tree in visualizer
        dot_data = StringIO()
        export_graphviz(self.classifier, out_file=dot_data,  
                filled=True, rounded=True,
                special_characters=True,feature_names = feature_cols, class_names=['0','1'])
        graph = pydotplus.graph_from_dot_data(dot_data.getvalue())  
        graph.write_png('decisiontree.png')
        Image(graph.create_png())

    def classify(self, dataset):
        global DEBUG
        if DEBUG:
            print("Classifying dataset...")

        #prepare dataset
        true_dataset = dataset.drop('entityID', axis=1)
        entityIDs = dataset['entityID']

        #classify data
        predictor_values = self.classifier.predict(true_dataset)
        
        joinedClassifications = {
            'entityID': entityIDs,
            'classification': predictor_values
        }

        if DEBUG:
            print("Commiting data to database")
        #flush to database
        counter = 0
        for entityID in joinedClassifications['entityID']:
            self.database.insertClassification(entityID, joinedClassifications['classification'][counter])
            counter = counter + 1

        print(joinedClassifications)
        return joinedClassifications

def initClassifier(import_ID):
    global DEBUG

    db = database()
    training_set = db.loadTrainingSet()
    dataset = db.loadDataset(import_ID)

    if DEBUG:
        print(training_set)

    cl = classifier(training_set, None, db)
    cl.trainDecisionTree()

    cl.classify(dataset)

initClassifier(41)
