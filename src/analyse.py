import pyodbc
import os
import sys
import nltk
import grammarbot
from nltk.corpus import stopwords
from nltk.tokenize import PunktSentenceTokenizer
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.stem import PorterStemmer
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

class database:
    def __init__(self, importID):
        self.conn = self.connect()
        self.listedData = []
        self.importID = importID

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

    """ Updates the status for the current import """
    def updateImport(self, status):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE feedbackhub.import SET status = ? WHERE import_ID = ?", status, self.importID)
        self.conn.commit()

    def fetchData(self):
        cursor = self.conn.cursor()   
        
        print("Fetching data from database. import_id {}".format(self.importID))

        cursor.execute("SELECT e.response_id, e.raw_data, e.entity_id\
                        FROM ((feedbackhub.entity AS e\
                        INNER JOIN feedbackhub.response AS r ON r.response_id = e.response_id)\
                        INNER JOIN feedbackhub.import AS i ON i.import_id = r.import_id)\
                        WHERE i.import_id = ?", self.importID)
        
        rows = cursor.fetchall()

        for response in rows:
            self.listedData.append(response)

    def insertAnalysis(self, entity, stopwords, lex_rich, filt_lex_rich, lex_diff, gram_incorrectness, comp, neg, neu, pos, tokens_length):
        #print("Inserting response into database")
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO feedbackhub.analysis (\
            entity_ID, stopwords, lexical_richness, stopword_lexical_richness,\
            lexical_richness_difference, grammatical_incorrectness,\
            sentiment_compound, sentiment_neg, sentiment_neu, sentiment_pos, token_length)\
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);", str(entity), stopwords, lex_rich, filt_lex_rich, lex_diff, gram_incorrectness, comp, neg, neu, pos, tokens_length)

        self.conn.commit()

    def insertTokens(self, tokens, entityID):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE feedbackhub.entity SET tokens = ? WHERE entity_id = ?", tokens, entityID)
        self.conn.commit()

    def insertSimilarity(self, entityID1, entityID2, similarity):
        print("INERTING {} {} ".format(entityID1, entityID2))
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO feedbackhub.similarities (entityID1, entityID2, similarity) VALUES (?, ?, ?)", entityID1, entityID2, similarity)
        self.conn.commit()

def tag(tokens):
    tagged = []
    for t in tokens:
        tagged.append(nltk.pos_tag(t))

    return tagged

def analyse(data):
    length = len(data.listedData)
    counter = 1

    stopword_array = []

    for d in data.listedData:
        print("Analysing entity {} / {}".format(counter, length))
        #We can perform some basic analysis here
        try:
            tokens = nltk.word_tokenize(d[1]) #tokenise the response
            tokens_length = len(tokens)

            #Fetch the stop_words and filter them with the responbses
            stop_words = set(stopwords.words('english'))
            filtered_response = [w for w in tokens if not w in stop_words]
            detokenize = ""
            
            for f in filtered_response:
                detokenize += f
                detokenize += " "
            
            data.insertTokens(detokenize, d[2]) #d[2] is entity id
            stopword_array.append([d[2], tokens])
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

            data.insertAnalysis(d[2], detokenize, lex_rich, filt_lex_rich, lex_diff, grammatical_incorrectness, comp, neg, neu, pos, tokens_length)

        except ZeroDivisionError:
            pass
        except Exception as e:
            print(e)
            exit(1)

        counter += 1

    return stopword_array

def determineSimilarEntities(stopword_array):
    print("Processing similarities")

    counter = 0
    data_length = len(stopword_array)

    for d in stopword_array:
        d_counter = counter
    
        #get stem word
        stem_a = getStemWords(d[1])
        venn_a = set(stem_a)

        #assess similarity
        while d_counter < data_length:
            stem_b = getStemWords(stopword_array[d_counter][1])
            venn_b = set(stem_b)
            venn_intersection = venn_a.intersection(venn_b)

            similarity = (float(len(venn_intersection)) / (len(venn_a) + len(venn_b) - len(venn_intersection))) * 100

            data.insertSimilarity(d[0], stopword_array[d_counter][0], similarity)

            d_counter += 1

        counter = counter + 1

def getStemWords(sentence):
    ps = PorterStemmer()
    stems = []

    for w in sentence:
        stems.append(ps.stem(w))

    return stems

def initAnalysis(importID):
    try:
        print("--------------")
        print("Begining Analysis...")
        print("Fetching data")
        data = database(importID)
        data.updateImport("Importing")
        data.fetchData()

        print("Analysing data")
        stopword_array = analyse(data)
        determineSimilarEntities(stopword_array)

    except Exception:
        data.updateImport("Failed")