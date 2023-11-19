import joblib
import nltk
from nltk.corpus import stopwords
import re
import requests
import psycopg2
from wordcloud import WordCloud
# Function to predict new text
# Download Indonesian stopwords
nltk.download('stopwords')

# # Get Indonesian stopwords
indonesian_stopwords = set(stopwords.words('indonesian'))

# Function to clean and preprocess text
def preprocess_text(text):
    # Lowercasing
    text = text.lower()
    
    # Remove special characters
    text = re.sub(r'\W', ' ', text)

    # Remove single characters
    text = re.sub(r'\s+[a-zA-Z]\s+', ' ', text)

    # Substituting multiple spaces with single space
    text = re.sub(r'\s+', ' ', text, flags=re.I)

    # Tokenization and stopword removal
    tokens = text.split()
    filtered_tokens = [word for word in tokens if word not in indonesian_stopwords]
    text = ' '.join(filtered_tokens)

    return text

def predict_hoax(new_text):
    # Preprocess the text
    preprocessed_text = preprocess_text(new_text)
    
    # Load the saved vectorizer and model
    loaded_vectorizer = joblib.load('config/tfidf_vectorizer.joblib')
    loaded_model = joblib.load('config/hoax_detection_model.joblib')
    
    # Transform the preprocessed text to tf-idf vector
    text_vector = loaded_vectorizer.transform([preprocessed_text]).toarray()
    
    # Predict using the loaded model
    prediction_probabilities = loaded_model.predict_proba(text_vector)
    
    # The first column corresponds to 'not hoax' and the second column to 'hoax'
    probability_not_hoax = prediction_probabilities[0][0]
    probability_hoax = prediction_probabilities[0][1]
    
    return probability_not_hoax, probability_hoax

import datetime

start = 1
end = 2

# reference date
date_to = str(datetime.datetime.now() - datetime.timedelta(days=start)).split(' ')[0]
date_from = str(datetime.datetime.now() - datetime.timedelta(days=end)).split(' ')[0]

# keyword for search news
all_key = ['pemilu 2024', 'Pemilu', 'Capres 2024', 'Cawapres 2024', 'Hasil Survey Pemilu', 'Isu Politik', 'Partai Politik', 'Peta Suara Pemilu', 'Survey dan Poling', 'Kampanye Pemilu']

# apikey to get news from newsapi
apkey = [
    '34f49fa2bcce496da0f3fb9e01733efb',
    '238781231b964762b5e372d5402d26bf',
    '0bbdc8553d724146b66bc41827f4d3ab',
    'b0f2048574b24fd194ee0c45fc91995a',
    'f92254a4e35a4bfbaa4620b8124a6d4c'
]

# inisialisasi query insert data news
sql_insert_data = "INSERT INTO data (source, author, title, description, url, publishedat, content, indikasi, keyword) values "

# looping get news from newsapi
for keyword in all_key:
    # looping apikey for change apikey if apikey having error
    for ke in apkey:        
        url_ = f'https://newsapi.org/v2/everything?q={keyword}&from={date_from}T00:00:00&to={date_to}T00:00:00&apiKey={ke}'
        response_get = requests.get(url_)

        if response_get.status_code == 429:
            continue
        else:
            break
    
    get_data = response_get.json()

    # loop result response api
    for g in get_data['articles']:
        source = g['source']['name']
        author = g['author']
        title = g['title']
        description = g['description']
        url = g['url']
        publishedAt = g['publishedAt'].split('T')[0]
        content = g['content'].split('[')[0]

        # detect content
        not_hoax_prob, hoax_prob = predict_hoax(content)

        # candidate query inserting data news
        sql_insert_data += f"('{source}', '{author}', '{title}', '{description}', '{url}', '{publishedAt}', '{content}', {hoax_prob*100}, '{keyword}'),"

sql_insert_data = sql_insert_data[:-1] + ";"

# inisialisasi db connection
conn = psycopg2.connect(
                    user="elohdfiuzkicdw",
                    password="a17ef52a5574fd9befa1a27abd708f8ae9671dfabf7baaf7221aeeccb77deb48",
                    host="ec2-44-206-204-65.compute-1.amazonaws.com",
                    port="5432",
                    database="d2m346aofb18ou"
                      )

# process delete old data and change to new data
# mart daily
sql_truncate_insert_mart_daily = "TRUNCATE TABLE data_mart_daily;INSERT INTO data_mart_daily (date, hoax, not_hoax) (SELECT publishedat, COUNT ( CASE WHEN indikasi >= 50 THEN id END ) AS hoax_total, COUNT ( CASE WHEN indikasi < 50 THEN id END ) AS nothoax_total FROM data GROUP BY 1 ORDER BY 1 DESC);"
# mart total
sql_truncate_insert_mart_total = "TRUNCATE TABLE data_mart_hoaxker;INSERT INTO data_mart_hoaxker (keyword, hoax) (SELECT keyword, COUNT(*) FROM data where indikasi >= 50 GROUP BY 1 ORDER BY 2 DESC);UPDATE data_mart_total SET total_data = (SELECT COUNT(*) FROM data), total_data_hoax = (SELECT COUNT(*) FROM data where indikasi >= 50), total_data_not_hoax = (SELECT COUNT(*) FROM data where indikasi < 50), total_data_daily = (SELECT COUNT(*) FROM data where publishedat = (SELECT publishedat FROM data ORDER BY publishedat DESC LIMIT 1)) WHERE id = 0"

# result all query
sql_all = sql_insert_data + sql_truncate_insert_mart_daily + sql_truncate_insert_mart_total 

# processing query on db
with conn.cursor() as upd_data:
    upd_data.execute(sql_all)
conn.commit()

# CREATING WORDCLOUD
# get data hoax
with conn.cursor() as get_data_hoax:
    get_data_hoax.execute("SELECT content from data where indikasi >= 50;")
    get_data_hoax = get_data_hoax.fetchall()
    
# get data not hoax
with conn.cursor() as get_data_nothoax:
    get_data_nothoax.execute("SELECT content from data where indikasi < 50;")
    get_data_nothoax = get_data_nothoax.fetchall()

# processing result data
hoax_text = ""
for w in get_data_hoax:
    hoax_text += preprocess_text(w[0])
    
nothoax_text = ""
for w in get_data_nothoax:
    nothoax_text += preprocess_text(w[0])

# generating wordcloud
cloud_hoax = WordCloud(collocations = False, scale=50).generate(hoax_text).words_
cloud_nothoax = WordCloud(collocations = False, scale=50).generate(nothoax_text).words_

# inisialisasi inserting into db mart wordcloud
sql_insert_wordcloud = "TRUNCATE TABLE data_mart_wordcloud;INSERT INTO data_mart_wordcloud (word, freq, status) values "
for ch in cloud_hoax:
    sql_insert_wordcloud += f"('{ch}', {cloud_hoax[ch]}, 'hoax'),"
    
for ch in cloud_nothoax:
    sql_insert_wordcloud += f"('{ch}', {cloud_nothoax[ch]}, 'hoax'),"

sql_insert_wordcloud = sql_insert_wordcloud[:-1] + ";"

# insert process
with conn.cursor() as upd_data:
    upd_data.execute(sql_insert_wordcloud)
conn.commit()
conn.close()