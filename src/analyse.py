import pyodbc
import os
import sys
import nltk
import grammarbot
import language_check
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
            raise e

    """ Updates the status for the current import """
    def updateImport(self, status):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE feedbackhub.import SET status = ? WHERE import_ID = ?", status, self.importID)
        self.conn.commit()

    def fetchData(self, analysed):
        cursor = self.conn.cursor()   
        
        print("Fetching data from database. import_id {}".format(self.importID))

        cursor.execute("SELECT e.response_id, e.raw_data, e.entity_id\
                        FROM ((feedbackhub.entity AS e\
                        INNER JOIN feedbackhub.response AS r ON r.response_id = e.response_id)\
                        INNER JOIN feedbackhub.import AS i ON i.import_id = r.import_id)\
                        WHERE i.import_id = ? AND e.analysed = ?", self.importID, analysed)
        
        rows = cursor.fetchall()

        listedData = []
        for response in rows:
            listedData.append(response)

        return listedData

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

    def insertSimilarity(self, entityID, similarities):
        try:
            cursor = self.conn.cursor()
            cursor.execute("INSERT INTO feedbackhub.similarities (entityID, similarities) VALUES (?, ?);", entityID, similarities)
            self.conn.commit()
        except pyodbc.IntegrityError as e:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE feedbackhub.similarities SET similarities = ? WHERE entityID = ?;",similarities,  entityID)
            self.conn.commit()


def tag(tokens):
    tagged = []
    for t in tokens:
        tagged.append(nltk.pos_tag(t))

    return tagged

def analyse(data, listedData):
    length = len(listedData)
    counter = 1

    stopword_array = []
    print(listedData)
    for d in listedData:
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
            stopword_array.append([d[2], filtered_response])
            #calculate the lexical richness of raw and filtered data
            filt_lex_rich = len(filtered_response) / len(d[1])
            lex_rich = len(set(d[1])) / len(d[1])
            
            lex_diff = lex_rich - filt_lex_rich

            #attempt to parse the response, we can see how far we get in the response before the grammar fails
            #thus, giving a numerical representation of the grammatical soundness of the response
            #(i.e., generate a percentage of the sentence that is grammatical)
            #We can use an API for this

            # This is slow but can hopefully find new API for this
            #grammar_client = GrammarBotClient(api_key='KS9C5N3Y')
            ltool = language_check.LanguageTool('en-GB')
            matches = ltool.check(d[1])
            incorrectness = len(matches)

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
            raise e
        counter += 1

    return stopword_array

def getStopwords(listedData):
    stopword_array = []

    for d in listedData:
        tokens = nltk.word_tokenize(d[1]) #tokenise the response
        stop_words = set(stopwords.words('english'))
        filtered_response = [w for w in tokens if not w in stop_words]            
        stopword_array.append([d[2], filtered_response])

    return stopword_array


def determineSimilarEntities(data, stopword_array):
    counter = 0
    data_length = len(stopword_array)
    print("Processing similarities")
    print(stopword_array)

    similarities_arr = []
    for d in stopword_array:
        #if after removing stopwords the token list is empty then just skip
        if len(d[1]) < 3: #not worth looking at
            continue
            
        d_counter = counter 
    
        #get stem word
        stem_a = getStemWords(d[1])
        venn_a = set(stem_a)

        #assess similarity
        similarities = 0
        while d_counter < data_length:
            if len(stopword_array[d_counter][1]) < 3: #not worth looking at
                d_counter += 1
                continue

            stem_b = getStemWords(stopword_array[d_counter][1])
            venn_b = set(stem_b)
            venn_intersection = venn_a.intersection(venn_b)

            similarity = (float(len(venn_intersection)) / (len(venn_a) + len(venn_b) - len(venn_intersection))) * 100

            if similarity > 15 and similarity < 100: #we need < 100 as we don't want to match it against itself
                print("Similarity {} >> \n {}. >> \n Accuracy: {} \n".format(d[1], stopword_array[d_counter][1], similarity))
                similarities += 1

            d_counter += 1
        
        #similarities_map.append([d[0], similarities])
        data.insertSimilarity(d[0], similarities)

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
        analysed_data = data.fetchData(1)
        unanalysed_data = data.fetchData(0)


        print("Analysing data")
        stopword_array = analyse(data, unanalysed_data)
        analysed_data_stop_words = getStopwords(analysed_data)

        if len(analysed_data_stop_words) > 0:
            for d in analysed_data_stop_words:
                stopword_array.append(d)

        determineSimilarEntities(data, stopword_array)

    except Exception as e:
        data.updateImport("Failed")
        raise e
        


