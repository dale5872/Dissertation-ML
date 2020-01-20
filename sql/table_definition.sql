CREATE TABLE feedback_hub.import (
    import_id INT NOT NULL IDENTITY PRIMARY KEY,
    import_date DATETIME NOT NULL DEFAULT GETDATE(),
    import_method VARCHAR(255) NOT NULL
);

CREATE TABLE feedback_hub.response (
    response_id INT NOT NULL IDENTITY PRIMARY KEY,
    import_id INT FOREIGN KEY REFERENCES feedback_hub.import(import_id)
);

CREATE TABLE feedback_hub.entity (
    entity_id INT NOT NULL IDENTITY PRIMARY KEY,
    response_id INT FOREIGN KEY REFERENCES feedback_hub.response(response_id),
    raw_data TEXT NOT NULL
);

CREATE TABLE feedback_hub.analysis (
    analysis_id INT NOT NULL IDENTITY PRIMARY KEY,
    entity_id INT FOREIGN KEY REFERENCES feedback_hub.entity(entity_id)
        ON DELETE CASCADE,
    stopwords TEXT NOT NULL,
    lexical_richness DECIMAL(18,10) NOT NULL,
    stopword_lexical_richness DECIMAL(18,10) NOT NULL,
    lexical_richness_difference DECIMAL(18,10) NOT NULL,
    grammatical_incorrectness DECIMAL(18,10) NOT NULL,
    sentiment_compound DECIMAL(18,10) NOT NULL,
    sentiment_neg DECIMAL(18,10) NOT NULL,
    sentiment_neu DECIMAL(18,10) NOT NULL,
    sentiment_pos DECIMAL(18,10) NOT NULL
);