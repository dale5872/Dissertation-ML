import pyodbc

class connector:
    @staticmethod
    def connect():
        server = "feedback-hub.database.windows.net"
        username = "development"
        password = "jd*nc&cmFhQ1£dfg"
        database = "FeedbackHub"
        driver= '{ODBC Driver 13 for SQL Server}'

        conn = pyodbc.connect('DRIVER='+driver+';SERVER='+server+';PORT=1433;DATABASE='+database+';UID='+username+';PWD='+ password)

        return conn.cursor()

cur = connector.connect()
cur.execute("SELECT * FROM INFORMATION_SCHEMA.TABLES;")
rows = cur.fetchone()

for row in rows:
    print(row)