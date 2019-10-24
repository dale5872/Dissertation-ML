import pyodbc
import argparse
import os
import sys
import nltk
import grammarbot
from nltk.corpus import stopwords
from nltk.tokenize import PunktSentenceTokenizer
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from grammarbot import GrammarBotClient

class Error(Exception):
    """Base class for exceptions"""
    pass

class ArgumentError(Error):
    """ Exception for missing arguments """
    def __init__(self, message):
        self.message = message

class ImportError(Error):
    """ Exception for missing arguments """
    def __init__(self, message):
        self.message = message

class arguments:
    def __init__(self):
        self.ARG_I = None
        self.ARG_R = None

    def parseargs(self):
        argparser = argparse.ArgumentParser(description="This script imports the data into the database for analysis")
        argparser.add_argument("--i", default=None, help="Specifies the file to import")

        #Now lets check the arguments
        args = argparser.parse_args()

        if args.i == None:
            raise ArgumentError("File was not specified, please try again")
        else:
            self.ARG_I = args.i

class data:
    def __init__(self):
        self.conn = self.connect()
        self.listedData = []

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

    def importData(self, args):
        cursor = self.conn.cursor()   
        
        print("Fetching data from database. import_id {}".format(args.ARG_I))

        cursor.execute("SELECT feedback_hub.entity.response_id, feedback_hub.entity.raw_data, feedback_hub.entity.entity_id\
                        FROM ((feedback_hub.entity\
                        INNER JOIN feedback_hub.response ON feedback_hub.response.response_id = feedback_hub.entity.response_id)\
                        INNER JOIN feedback_hub.import ON feedback_hub.import.import_id = feedback_hub.response.import_id)\
                        WHERE feedback_hub.import.import_id = ?", args.ARG_I)
        
        rows = cursor.fetchall()

        for response in rows:
            self.listedData.append(response)

    def insertAnalysis(self, entity, stopwords, lex_rich, filt_lex_rich, lex_diff, gram_incorrectness, comp, neg, neu, pos):
        cursor = self.conn.cursor()


        cursor.execute("INSERT INTO feedback_hub.analysis (\
            entity_id, stopwords, lexical_richness, stopword_lexical_richness,\
            lexical_richness_difference, grammatical_incorrectness,\
            sentiment_compound, sentiment_neg, sentiment_neu, sentiment_pos)\
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);", str(entity), stopwords, lex_rich, filt_lex_rich, lex_diff, gram_incorrectness, comp, neg, neu, pos)

        self.conn.commit()

def tag(tokens):
    tagged = []
    for t in tokens:
        tagged.append(nltk.pos_tag(t))

    return tagged

def analyse(database):
    length = len(data.listedData)
    counter = 1

    for d in data.listedData:
        #We can perform some basic analysis here
        try:
            tokens = nltk.word_tokenize(d[1]) #tokenise the response

            #Fetch the stop_words and filter them with the responbses
            stop_words = set(stopwords.words('english'))
            filtered_response = [w for w in tokens if not w in stop_words]
            detokenize = ""
            
            for f in filtered_response:
                detokenize += f
                detokenize += " "
            
            #calculate the lexical richness of raw and filtered data
            filt_lex_rich = len(filtered_response) / len(d[1])
            lex_rich = len(set(d[1])) / len(d[1])
            
            lex_diff = lex_rich - filt_lex_rich

            #attempt to parse the response, we can see how far we get in the response before the grammar fails
            #thus, giving a numerical representation of the grammatical soundness of the response
            #(i.e., generate a percentage of the sentence that is grammatical)
            #We can use an API for this

            # This is slow but can hopefully find new API for this
            grammar_client = GrammarBotClient(api_key='KS9C5N3Y')
            res = grammar_client.check(d[1])
            incorrectness = len(res.matches)

            grammatical_incorrectness = incorrectness / len(d[1])

            #We can also get some more information though sentiment analysis
            #which estimates the negativity, neutrality or positivity of a sentence
            sid = SentimentIntensityAnalyzer()
            ss = sid.polarity_scores(d[1])

            sorted_ss = sorted(ss)
            comp = ss[sorted_ss[0]]
            neg = ss[sorted_ss[1]]
            neu = ss[sorted_ss[2]]
            pos = ss[sorted_ss[3]]
            
            #Print the data to the screen (for debugging)
            #print("ID: {}. Raw: {}".format(d[0], d[1]))
            #print("Lexical Richness: {}".format(lex_rich))
            #print("Filtered Lexical Richness: {}".format(filt_lex_rich))
            #print("Lexical Richness Difference: {}".format(lex_diff))
            #print("Grammatical Incorrectness: {}".format(grammatical_incorrectness))
            #print("Compound: {0}, Negativity: {1}, Neutrality: {2}, Positivity: {3}".format(comp, neg, neu, pos))
            #print("\n")

            percent = int((counter / length)*100)
            sys.stdout.write('\r')
            sys.stdout.write("[" + str(percent) + "%]")
            sys.stdout.flush()

            database.insertAnalysis(d[2], detokenize, lex_rich, filt_lex_rich, lex_diff, grammatical_incorrectness, comp, neg, neu, pos)

            counter += 1
        except ZeroDivisionError:
            pass


args = arguments()
args.parseargs()

print("Importing data")
data = data()
data.importData(args)

print("Analysing data")
analyse(data)