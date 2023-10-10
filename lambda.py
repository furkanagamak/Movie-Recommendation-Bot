import os
import urllib3
import json

def get_slots(intent_request):
    return intent_request['currentIntent']['slots']
    
def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message, response_card):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message,
            'responseCard': response_card
        }
    }
    
def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }
    return response

def closeWithResponseCard(session_attributes, fulfillment_state, message, response_card):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message,
            'responseCard': response_card
        }
    }
    return response    


def closeWelcomeIntent(session_attributes, fulfillment_state, message, response_card):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message,
            'responseCard': response_card
        }
    }
    return response
    
def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }
    

def build_response_card(title, subtitle, options):
    buttons = None
    if options is not None:
        buttons = []
        for i in range(min(5, len(options))):
            buttons.append(options[i])

    return {
        'contentType': 'application/vnd.amazonaws.card.generic',
        'version': 1,
        'genericAttachments': [{
            'title': title,
            'subTitle': subtitle,
            'buttons': buttons
        }]
    }

def create_movie_cards(titles, links, posters, scores):
    num_movies = min(10, len(titles))
    cards = [
        {
            'title': titles[i],
            'subTitle': 'Rating: {}'.format(scores[i]),
            'imageUrl': posters[i],
            'attachmentLinkUrl': links[i]
        }
        for i in range(num_movies)
    ]

    return {
        'contentType': 'application/vnd.amazonaws.card.generic',
        'version': 1,
        'genericAttachments': cards
    } 

def build_options(slot):
    if slot == 'category':
        return [
            {'text': 'Top Rated', 'value': '1'},
            {'text': 'Most Popular', 'value': '2'},
            {'text': 'Newly Released', 'value': '3'},
            {'text': 'Trending Today', 'value': '4'}
        ]

def build_intent_suggestions(intentName):
    if intentName == 'Welcome':
        return [
            {'text': 'Recommending Movies', 'value': 'suggest movies'}
        ]


def build_validation_result(is_valid, violated_slot, message_content):
    return {
        'isValid': is_valid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }
    
def validate_choosen_category(category):
    if category not in ["1","2","3","4"]:
        return build_validation_result(False, 'category', 'Choose from the given categories.')
    return build_validation_result(True, None, None)
    
def fetch_movie(intent_data):
    selected_category = get_slots(intent_data)["category"]
    invocation_type = intent_data['invocationSource']
    session_attributes = intent_data['sessionAttributes'] if intent_data['sessionAttributes'] is not None else {}

    if invocation_type == 'DialogCodeHook':
        filled_slots = get_slots(intent_data)
        category_validation = validate_choosen_category(selected_category)
        
        if not category_validation['isValid']:
            filled_slots[category_validation['violatedSlot']] = None
            filled_slots['category'] = None
            return elicit_slot(
                session_attributes,
                intent_data['currentIntent']['name'],
                filled_slots,
                category_validation['violatedSlot'],
                category_validation['message'],
                build_response_card(
                    'Choose a {}'.format(category_validation['violatedSlot']),
                    category_validation['message']['content'],
                    build_options(category_validation['violatedSlot'])
                )
            )
        session_attributes = intent_data['sessionAttributes'] if intent_data['sessionAttributes'] is not None else {}
        return delegate(session_attributes, filled_slots)

    movie_list, movie_identifiers, movie_images, movie_ratings = [], [], [], []

    if selected_category == "1":
        movie_list, movie_identifiers, movie_images, movie_ratings = fetch_top_rated_movies(selected_category)
    elif selected_category == "2":
        movie_list, movie_identifiers, movie_images, movie_ratings = fetch_popular_movies(selected_category)
    elif selected_category == "3":
        movie_list, movie_identifiers, movie_images, movie_ratings = fetch_newly_released_movies(selected_category)
    elif selected_category == "4":
        movie_list, movie_identifiers, movie_images, movie_ratings = fetch_trending_movies_today(selected_category)
    else:
        return close(intent_data['sessionAttributes'],
                     'Fulfilled',
                     {'contentType': 'PlainText',
                      'content': "I can't help with that request."})

    movie_sources = fetch_movie_providers(movie_identifiers)
    response_content = {
        "1": 'The top rated movies are:',
        "2": 'The most popular movies are:',
        "3": 'The newly released movies are:',
        "4": 'The movies trending today are:'
    }

    return closeWithResponseCard(intent_data['sessionAttributes'],
                                 'Fulfilled',
                                 {'contentType': 'PlainText',
                                  'content': response_content[selected_category]},
                                  create_movie_cards(movie_list, movie_sources, movie_images, movie_ratings)
                                 )


def fetch_top_rated_movies(category):
    return fetch_movies_from_api("top_rated")

def fetch_newly_released_movies(category):
    return fetch_movies_from_api("now_playing")

def fetch_popular_movies(category):
    return fetch_movies_from_api("popular")

def fetch_trending_movies_today(category):
    return fetch_movies_from_api("trending/movie/day")

def fetch_movie_providers(movie_ids):
    api_key = os.environ.get('api_key')
    http_manager = urllib3.PoolManager()
    providers = []
    
    for movie_id in movie_ids:
        response = http_manager.request('GET', "https://api.themoviedb.org/3/movie/{}/watch/providers?api_key={}".format(movie_id, api_key))
        decoded_response = json.loads(response.data.decode('utf-8'))
        provider_data = decoded_response['results']
        
        if "US" in provider_data:
            link = provider_data["US"]["link"]
            providers.append(link)
        else:
            providers.append("https://cutt.ly/5QGm4jF")
    return providers

def fetch_movies_from_api(endpoint):
    api_key = os.environ.get('api_key')
    http_manager = urllib3.PoolManager()
    response = http_manager.request('GET', f"https://api.themoviedb.org/3/movie/{endpoint}?api_key={api_key}&language=en-US&page=1")
    decoded_response = json.loads(response.data.decode('utf-8'))
    movie_data = decoded_response['results']

    titles = [movie['title'] for movie in movie_data]
    ids = [movie['id'] for movie in movie_data]
    posters = ["https://image.tmdb.org/t/p/original" + movie['poster_path'] for movie in movie_data]
    ratings = [movie['vote_average'] for movie in movie_data]
    
    return [titles, ids, posters, ratings]

    
def dispatch(intent_request):
    intent_name = intent_request['currentIntent']['name']
    if intent_name == 'RecommendMovie':
        return fetch_movie(intent_request)
    if intent_name == 'Welcome':
        return closeWelcomeIntent(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': 'Hello, how can I help you?'},
                  build_response_card(
                      "I can help you with:",
                      "choose an option",
                      build_intent_suggestions(intent_name)
                  )
                  )

    raise Exception('Intent with name ' + intent_name + ' not supported')

def lambda_handler(event, context):
    return dispatch(event)
