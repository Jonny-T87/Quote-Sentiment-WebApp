from flask import Flask, render_template, request, url_for, Markup
import os
import json
import pandas as pd
import numpy as np
from random import randrange
from h2o_wave import main, app, Q, ui # install h20 AI

import nltk
nltk.download('vader_lexicon')

from nltk.sentiment.vader import SentimentIntensityAnalyzer

app = Flask(__name__)

#setting H20 AI Cloud API 
with open('C:\Program Files\Git\.secret\H2O_GPTe_api.json') as f:
    login = json.load(f)

H2O_GENAI_API_ADDRESS = login['address']
H2O_GENAI_API_KEY = login['api_key']

# load quotes in memory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# declare global variable
quotes = None


@app.before_request
def prepare_sentiment_quote_stash():
    global quotes

    # load the quote stash
    quotes = pd.read_csv(os.path.join(BASE_DIR, 'quotes.csv'))

    sid = SentimentIntensityAnalyzer()

    all_compounds = []
    for sentence in quotes['quote']:
        ss = sid.polarity_scores(sentence)
        for k in sorted(ss):
            if k == 'compound':
                all_compounds.append(ss[k])


    # add sentiment to the data
    quotes['sentiment_score'] = all_compounds

    # create ladder index
    quotes = quotes.sort_values('sentiment_score')
    quotes['index'] = [ix for ix in range(0, len(quotes))]



def gimme_a_quote(direction = None, current_index = None, max_index_value = 0):
    rand_index = randrange(max_index_value)
    darker = None
    brighter = None


    # New session visit
    if current_index is None:
        brighter = rand_index

    if direction == 'brighter':
        brighter = current_index
    else:
        darker = current_index

    if darker is not None:
        try:
            current_index = int(darker)
        except ValueError:
            # somebody is gaming the system
            current_index = rand_index


        if current_index > 0:
            # try for a lesser value than current one
            rand_index = randrange(0, current_index)
        else:
            # already at lowest point so assign a new random of full set
            rand_index = rand_index


    elif brighter is not None:
        try:
            current_index = int(brighter)
        except ValueError:
            # somebody is gaming the system
            current_index = rand_index

        # try for a higher value than current one
        if current_index < max_index_value -1:
            rand_index = randrange(current_index, max_index_value)
        else:
            # already at highest point so assign a new random of full set
            rand_index = rand_index
    else:
        # grab a random value
        rand_index = rand_index

    return (rand_index)

def get_h2o_genai_mood_recommendation(quote, mood):
    try:
        #preping the payload for H2O GenAI
        prompt_payload = {
            "prompt": f'Based on the quote: "{quote}" and the user’s mood being "{mood}", provide either mood improvement advice or explain what the author of the quote might have meant by it. Please give relevant recommendations.',
            "max_tokens": 150
        }

        #Making the API callto H2O GenAI
        response = requests.post(H2O_GENAI_API_ADDRESS, json=prompt_payload, headers={'api_key': f"Bearer {H2O_GENAI_API_KEY}"}
        )
        
        #Parse the response
        if response.status_code == 200:
            response_json = response.json()
            return response_json['generated_text']
        else:
            return "Sorry, I couldn't generate a clickbait prompt. Please try again later."
    except Exception as e:
        return f"Error: {str(e)}"

@app.route("/")
def quote_me():
    quote_stash_tmp = quotes.copy()
    max_index_value = np.max(quote_stash_tmp['index'].values)
    rand_index_value = randrange(max_index_value)

    darker = request.args.get("darker")
    brighter = request.args.get("brighter")

    if darker is not None:       
        try:
        	current_index = int(darker)
            user_mood = 'darker'
        except ValueError:
            # somebody is gaming the system
            current_index = randrange(max_index_value)

        new_index = gimme_a_quote(direction =  'darker', current_index = current_index, max_index_value = max_index_value)

    elif brighter is not None:
        try:
            current_index = int(brighter)
            user_mood = 'brighter'
        except ValueError:
            # somebody is gaming the system
            current_index = rand_index_value

        new_index = gimme_a_quote(direction =  'brighter', current_index = current_index, max_index_value = max_index_value)

    else:
    	# grab a random value
    	new_index = randrange(max_index_value)
        user_mood = 'neutral' #Default mood for random quotes

random_quote = quote_stash_tmp.iloc[new_index]
# get a random integer between 0 and max_index_value
quote=random_quote['quote']
author = random_quote['author']
current_id =  random_quote['index']

    #Generate a clickbait prompt using H2O GenAI
clickbait_prompt = get_h2o_genai_mood_recommendation(quote, user_mood)

return render_template("quote.html",
                       quote = quote,
                       author = author,
                       current_id = current_id,
                       clickbait_prompt = clickbait_prompt
                       )