from django.shortcuts import render
from django.db import connection as conn
from django.http import JsonResponse

# Create your views here.
def dashboard(request):
    with conn.cursor() as get_mart_total:
        get_mart_total.execute('SELECT id, total_data, total_data_hoax, total_data_not_hoax, total_data_daily FROM data_mart_total where id = 0')
        get_mart_total = get_mart_total.fetchall()

    context = {
        'data_mart_total': get_mart_total[0]
    }

    return render(request, 'index/index.html', context)

def getAllData(request):
    with conn.cursor() as get_mart_daily:
        get_mart_daily.execute('SELECT id, CAST(date AS TEXT), hoax, not_hoax FROM data_mart_daily ORDER BY date DESC LIMIT 7')
        get_mart_daily = get_mart_daily.fetchall()

    with conn.cursor() as get_all_data:
        get_all_data.execute('SELECT id, title, source, ROUND( indikasi::numeric, 2 ), url FROM data ORDER BY publishedat DESC LIMIT 10')
        get_all_data = get_all_data.fetchall()

    with conn.cursor() as get_5_data_hoax:
        get_5_data_hoax.execute('SELECT keyword, hoax FROM data_mart_hoaxker ORDER BY hoax DESC LIMIT 5')
        get_5_data_hoax = get_5_data_hoax.fetchall()

    

    data_date = []
    data_hoax = []
    data_nothoax = []
    for d in range(len(get_mart_daily)):
        d += 1

        data_date.append(get_mart_daily[len(get_mart_daily)-d][1])
        data_hoax.append(get_mart_daily[len(get_mart_daily)-d][2])
        data_nothoax.append(get_mart_daily[len(get_mart_daily)-d][3])

    context = {
        'data_mart_daily': get_mart_daily,
        'data_all':get_all_data,
        'data_date' : data_date,
        'data_hoax' : data_hoax,
        'data_nothoax' : data_nothoax,
        'keyword_hoaxker' : get_5_data_hoax
    }

    return JsonResponse(context)

import joblib
import nltk
from nltk.corpus import stopwords
import re
# Function to predict new text
# Download Indonesian stopwords
nltk.download('stopwords')

# # Get Indonesian stopwords
indonesian_stopwords = set(stopwords.words('indonesian'))

# # Helper Function
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
    loaded_vectorizer = joblib.load('APPS/config/tfidf_vectorizer.joblib')
    loaded_model = joblib.load('APPS/config/hoax_detection_model.joblib')
    
    # Transform the preprocessed text to tf-idf vector
    text_vector = loaded_vectorizer.transform([preprocessed_text]).toarray()
    
    # Predict using the loaded model
    prediction_probabilities = loaded_model.predict_proba(text_vector)
    
    # The first column corresponds to 'not hoax' and the second column to 'hoax'
    probability_not_hoax = prediction_probabilities[0][0]
    probability_hoax = prediction_probabilities[0][1]
    
    return probability_not_hoax, probability_hoax


def checkNewsData(request):
    data_news = request.GET.get("news")
    not_hoax_prob, hoax_prob = predict_hoax(data_news)
    not_hoax_prob = not_hoax_prob*100
    hoax_prob = hoax_prob*100
    
    if not_hoax_prob >= hoax_prob:
        simpulan = 'BUKAN BERITA HOAKS'
    else:
        simpulan = 'BERITA HOAKS'

    context = {
        'probability_not_hoax' : round(not_hoax_prob, 2),
        'probability_hoax' : round(hoax_prob, 2),
        'simpulan': simpulan
    }
    return JsonResponse(context)