import os
import sys
import pyodbc
import pandas as pd
from sklearn.tree import DecisionTreeClassifier, export_graphviz
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.externals.six import StringIO  
#from IPython.display import Image  
#import pydotplus

DEBUG = True
TEST_FLAG = False

class Error(Exception):
    """Base class for exceptions"""
    pass

class EmptyTrainingSet(Error):
    """ Exception for empty training set """
    def __init__(self, message):
        self.message = message

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

    """ Updates the status for the current import """
    def updateImport(self, status, importID):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE feedbackhub.import SET status = ? WHERE import_ID = ?", status, importID)
        self.conn.commit()


    def loadDataset(self, import_ID):
        global DEBUG

        if DEBUG:
            print("Loading Live Data")

        cursor = self.conn.cursor()
        cursor.execute("SELECT a.entity_ID, a.stopword_lexical_richness, a.grammatical_incorrectness, a.lexical_richness, \
        a.sentiment_compound, a.token_length \
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
        sentiment_compound = []
        token_length = []

        for entity in rows:
            entityID.append(entity[0])
            stop_word_lexical_richness.append(entity[1])
            grammatical_incorrectness.append(entity[2])
            lexical_richness.append(entity[3])
            sentiment_compound.append(entity[4])
            token_length.append(entity[5])

        dataset = {
            'entityID': entityID,
            'stopword_lexical_richness': stop_word_lexical_richness,
            'grammatical_incorrectness': grammatical_incorrectness,
            'lexical_richness': lexical_richness,
            'sentiment_compound': sentiment_compound,
            'token_length': token_length
        }

        return pd.DataFrame(dataset)

    def loadDefaultTrainingSet(self):
        global DEBUG

        if DEBUG:
            print("Loading Training Data")

        cursor = self.conn.cursor()
        
        """
        cursor.execute("SELECT TOP 92 \
        convert(VARCHAR, t.stopword_lexical_richness), \
        convert(VARCHAR, t.grammatical_incorrectness), \
        convert(VARCHAR, t.lexical_richness), \
        t.classification \
         FROM feedbackhub.training_set AS t;") #Model 1

        
        cursor.execute("SELECT \
        convert(VARCHAR, t.stopword_lexical_richness), \
        convert(VARCHAR, t.grammatical_incorrectness), \
        convert(VARCHAR, t.lexical_richness), \
        t.classification \
         FROM feedbackhub.training_set AS t;") #Model 2

        """
        cursor.execute("SELECT \
        convert(VARCHAR, t.stopword_lexical_richness), \
        convert(VARCHAR, t.grammatical_incorrectness), \
        convert(VARCHAR, t.lexical_richness), \
        convert(VARCHAR, t.sentiment_compound), \
        t.token_length, t.classification \
        FROM feedbackhub.training_set AS t") #Model 3

        rows = cursor.fetchall()

        if len(rows) == 0 and DEBUG:
            raise EmptyTrainingSet("No training set")

        return self.formatTrainingData(rows)

    def loadTrainingSet(self, userID):
        global DEBUG

        if DEBUG:
            print("Loading User Based Training Data")

        cursor = self.conn.cursor()

        cursor.execute("SELECT a.stopword_lexical_richness, a.grammatical_incorrectness, a.lexical_richness, a.sentiment_compound, a.token_length, c.classification \
            FROM (((((feedbackhub.analysis AS a \
                INNER JOIN feedbackhub.classifications AS c ON a.entity_ID = c.entity_ID) \
                    INNER JOIN feedbackhub.entity AS e ON e.entity_ID = a.entity_ID) \
                        INNER JOIN feedbackhub.response AS r ON r.response_ID = e.response_ID) \
                            INNER JOIN feedbackhub.import AS i ON r.import_ID = i.import_ID) \
                                INNER JOIN feedbackhub.user_accounts AS u ON u.user_ID = i.user_ID) \
            WHERE u.user_ID = {};".format(userID))

        rows = cursor.fetchall()

        if len(rows) == 0:
            if DEBUG:
                print("User has no training data, loading defualt training set")
            return self.loadDefaultTrainingSet()
        
        return self.formatTrainingData(rows)

    def formatTrainingData(self, rows):
        stop_word_lexical_richness = []
        grammatical_incorrectness = []
        lexical_richness = []
        sentiment_compound = []
        token_length = []
        classification = []

        counter = 0
        for response in rows:
            stop_word_lexical_richness.append(response[0])
            grammatical_incorrectness.append(response[1])
            lexical_richness.append(response[2])
            #classification.append(response[3])

            sentiment_compound.append(response[3])
            token_length.append(response[4])
            classification.append(response[5])
            counter = counter + 1
        
        if DEBUG:
            print("Loaded {} rows for training set. {} rows used for training and {} rows used for evaluation".format(counter, (counter*0.8), (counter*0.2)))

        training_set = {
            'stopword_lexical_richness': stop_word_lexical_richness,
            'grammatical_incorrectness': grammatical_incorrectness,
            'lexical_richness': lexical_richness,
            'sentiment_compound': sentiment_compound,
            'token_length': token_length,
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
        global DEBUG, TEST_FLAG
        if DEBUG:
            print("Creating Training Model...")

        feature_cols = ['stopword_lexical_richness', 'grammatical_incorrectness', 'lexical_richness', 'sentiment_compound', 'token_length']

        X = self.training_set.drop('classification', axis=1)
        Y = self.training_set['classification']

        """ Set the training set size to 80%, where the remaining 20% will be tested
        on the trained model """
        X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size = 0.2)

        if DEBUG:
            print("Initialising Classifier")

        self.classifier = DecisionTreeClassifier(criterion="gini", splitter="best", max_depth=3, min_samples_split = 20, min_samples_leaf = 20)
        self.classifier.fit(X_train, Y_train)

        if DEBUG:
            print("Analysing Model Correctness")

        #Lets verify the model
        Y_pred = self.classifier.predict(X_test)

        matrix = confusion_matrix(Y_pred, Y_test)
        correct = matrix[0][0] + matrix[1][1]
        incorrect = matrix[0][1] + matrix[1][0]
        total = correct + incorrect

        accuracy = (correct / total) * 100

        if TEST_FLAG:
            print(matrix)
            print(classification_report(Y_pred, Y_test))
        
        return accuracy

        """
        #Output decision tree in visualizer
        dot_data = StringIO()
        export_graphviz(self.classifier, out_file=dot_data,  
                filled=True, rounded=True,
                special_characters=True,feature_names = feature_cols, class_names=['0','1'])
        graph = pydotplus.graph_from_dot_data(dot_data.getvalue())  
        graph.write_png('decisiontree.png')
        Image(graph.create_png())
        """

    def testTrainingTree(self):
        TEST_NUMBER = 500

        accuracy = 0
        highest = 0
        lowest = 100
        for i in range(TEST_NUMBER):
            current_accuracy = self.trainDecisionTree(False)
            accuracy = accuracy + current_accuracy
            if current_accuracy > highest:
                highest = current_accuracy
            if current_accuracy < lowest:
                lowest = current_accuracy
            print("Evaluating Model {}/{}".format(i, TEST_NUMBER))

        return_value = {
            'Average': accuracy / TEST_NUMBER,
            'Highest': highest,
            'Lowest': lowest
        }
        return return_value

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

def initClassifier(import_ID, userID):
    global DEBUG
    try:
        db = database()
        db.updateImport("Classifying", import_ID)
        training_set = db.loadTrainingSet(userID)
        dataset = db.loadDataset(import_ID)

        if DEBUG:
            print(training_set)

        cl = classifier(training_set, None, db)

        if DEBUG:
            print("Creating Deccision Tree. Finding tree with 90+ accuracy")
        accuracy = 0
        tree_counter = 0
        """
        We want an accurate decision tree, while the majority of decision trees
        created will be 90%+ accurate, occasionally we may face a tree that is as low
        as 75% accurate. Thus, we will only use trees that are 90% accurate.
        However, as this could be very CPU intensive, we will only try 5 times
        """
        while accuracy < 89 and tree_counter < 5:
            if DEBUG:
                print("TREE ACCURACY {}%".format(accuracy))
            accuracy = cl.trainDecisionTree()
            tree_counter = tree_counter + 1

        if DEBUG:
            print("Found tree with {}% Accuracy".format(accuracy))

        cl.classify(dataset)

        db.updateImport("Complete", import_ID)
    except EmptyTrainingSet as e:
        #Do nothing
        db.updateImport("Failed", import_ID)
    except Exception as e:
        db.updateImport("Failed", import_ID)
        print(e)

def evaluateClassifier():
    db = database()
    training_set = db.loadTrainingSet()

    cl = classifier(training_set, None, db)

    print("Results: {}%".format(cl.testTrainingTree()))
    accuracy = cl.trainDecisionTree()
    print("{}%".format(accuracy))

if TEST_FLAG:
    evaluateClassifier()