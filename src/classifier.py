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

    def load(self):
        global DEBUG

        if DEBUG:
            print("Loading Live Data")

        cursor = self.conn.cursor()
        cursor.execute("SELECT a.analysisID, a.stop_word_lexical_richness, \
        a.grammatical_incorrectness \
        FROM feedbackhub.analysis AS a")

        rows = cursor.fetchall()

        dataset = []
        for response in rows:
            dataset.append(response)

        return dataset

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

class classifier:
    def __init__(self, training_set, dataset):
        self.dataset = dataset
        self.training_set = training_set

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

        classifier = DecisionTreeClassifier()#criterion="gini", splitter="best",max_depth=3)
        classifier.fit(X_train, Y_train)

        if DEBUG:
            print("Analysing Model Correctness")

        #Lets verify the model
        Y_pred = classifier.predict(X_test)

        print(confusion_matrix(Y_pred, Y_test))
        print(classification_report(Y_pred, Y_test))

        #Output decision tree in visualizer
        dot_data = StringIO()
        export_graphviz(classifier, out_file=dot_data,  
                filled=True, rounded=True,
                special_characters=True,feature_names = feature_cols, class_names=['0','1'])
        graph = pydotplus.graph_from_dot_data(dot_data.getvalue())  
        graph.write_png('decisiontree.png')
        Image(graph.create_png())


def initClassifier():
    global DEBUG

    db = database()
    training_set = db.loadTrainingSet()

    if DEBUG:
        print(training_set)

    cl = classifier(training_set, None)
    cl.trainDecisionTree()

initClassifier()
