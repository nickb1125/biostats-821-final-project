import argparse
from objects.model import XGBoostModel
from objects.model_reload import model_retrain
from objects.current_state import current_state
import datetime 
import pickle
import os

def updater():
    if not (os.path.exists("data/current_state_object.pickle")):
        print("Data is being downloaded - downloading - this will take ~1 min and will only be done once...")
        now = current_state()
        with open('data/current_state_object.pickle', 'wb') as handle:
            pickle.dump(now, handle, protocol=pickle.HIGHEST_PROTOCOL)
    else:
        with open('data/current_state_object.pickle', 'rb') as handle:
            now = pickle.load(handle) # Note that all updates are done within object, so if time has passed between uses thats ok

    # Update if its a new season
    if ((now.year != datetime.datetime.now().year - 1) & (datetime.datetime.now().month <= 8)) or ((now.year == datetime.datetime.now().year) & (datetime.datetime.now().month > 8)):
        "Data loaded is from last season! Downloading data from this year - this will take ~1 min and only happen once..."
        now = current_state()
        with open('data/current_state_object.pickle', 'wb') as handle:
            pickle.dump(now, handle, protocol=pickle.HIGHEST_PROTOCOL)
    return now

def predict_series():
    now = updater()
    higher_team_abb = input("Input an abbreviation for the higher seeded team (i.e. 'BOS', 'ATL', 'BKN', etc): ")
    lower_team_abb = input("Input an abbreviation for the lower seeded team (i.e. 'BOS', 'ATL', 'BKN', etc): ")
    how_many_won_higher = int(input("Input how many games in the series the higher seed has already won (i.e. 0-4): "))
    how_many_won_lower = int(input("Input how many games in the series the lower seed has already won (i.e. 0-4): "))
    days_from_today = int(input("Input how many days from today the first game will be on (i.e. 0-30 - this is to approximate and account for the proper injury projections): "))
    now.predict_series(higher_seed_abb=higher_team_abb, lower_seed_abb=lower_team_abb, 
                   higher_already_won=how_many_won_higher, lower_already_won=how_many_won_lower,
                   for_simulation = False, series_starts_in_how_many_games=days_from_today)

def simulate_playoffs_from_this_point():
    now = updater()
    now.simulate_playoffs_from_this_point()

def get_probs_of_each_round():
    now = updater()
    now.get_probs_of_each_round()

def predict_matchup():
    now = updater()
    home_team_abb = input("Input an abbreviation for the home team (i.e. 'BOS', 'ATL', 'BKN', etc): ")
    away_team_abb = input("Input an abbreviation for the away team (i.e. 'BOS', 'ATL', 'BKN', etc): ")
    days_from_today = int(input("Input how many days from today the game will be played (i.e. 0-30 - this is to approximate and account for the proper injury projections): "))
    print('\n')
    now.predict_matchup(home_team_abb, away_team_abb, games_ahead_of_today = days_from_today / 2, for_simulation=False)

parser = argparse.ArgumentParser(description='Run NBA playoff prediction functions')

# Add arguments for each function
parser.add_argument('--predict_series', action='store_true', help='Predict the winner of a playoff series')
parser.add_argument('--simulate_playoffs_from_this_point', action='store_true', help='Simulate the playoffs from a certain point')
parser.add_argument('--get_probs_of_each_round', action='store_true', help='Get the probability of each team making it to each round')
parser.add_argument('--predict_matchup', action='store_true', help='Predict the winner of a playoff matchup')
parser.add_argument('--model_retrain', action='store_true', help='Retrain stored model.')

args = parser.parse_args()

if args.predict_series:
    predict_series()
    
if args.simulate_playoffs_from_this_point:
    simulate_playoffs_from_this_point()
    
if args.get_probs_of_each_round:
    get_probs_of_each_round()
    
if args.predict_matchup:
    predict_matchup()

if args.model_retrain:
    model_retrain()