# IF IMPORTS BELOW DONT WORK---->
# export PYTHONPATH="{insert your overarching folder path here (above /cli)}"

import argparse
from objects.model import XGBoostModel
from objects.model_reload import model_retrain
import datetime 
import pickle
import os

model_retrain()

if not (os.path.exists("data/current_state_object.pickle")):
    "Data is not downloaded - downloading - this will take ~1 min and will only be done once..."
    now = current_state.current_state()
    with open('data/current_state_object.pickle', 'wb') as handle:
        pickle.dump(now, handle, protocol=pickle.HIGHEST_PROTOCOL)
else:
    with open('data/current_state_object.pickle', 'rb') as handle:
         now = pickle.load(handle) # Note that all updates are done within object, so if time has passed between uses thats ok

# Update if its a new season
if ((now.year != datetime.datetime.now().year - 1) & (datetime.datetime.now().month <= 8)) or ((now.year == datetime.datetime.now().year) & (datetime.datetime.now().month > 8)):
    "Data loaded is from last season! Downloading data from this year - this will take ~1 min and only happen once..."
    now = current_state.current_state()
    with open('data/current_state_object.pickle', 'wb') as handle:
        pickle.dump(now, handle, protocol=pickle.HIGHEST_PROTOCOL)


####################### KEEP ALL CODE ABOVE AND UPDATE THE BELOW CODE TO BE A COMMAND LINE INTERFACE FOR EACH OF THE 4 FUNCTIONS...

# -------------> THERE SHOULD BE THE FOLLOWING 4 COMMANDS THAT RETURN EACH CORRESPONDING OUTPUT

################################################################

# Test single game prediction (FUNCTION 1)

print("First we are testing the basic game predicting functionality. \n")
home_team_abb = input("Input an abbreviation for the home team (i.e. 'BOS', 'ATL', 'BKN', etc): ")
away_team_abb = input("Input an abbreviation for the away team (i.e. 'BOS', 'ATL', 'BKN', etc): ")
days_from_today = int(input("Input how many days from today the game will be played (i.e. 0-30 - this is to approximate and account for the proper injury projections): "))
print('\n')
now.predict_matchup(home_team_abb, away_team_abb, games_ahead_of_today = days_from_today / 2, for_simulation=False)

# test series prediction (FUNCTION 2)

print("\nNow we test the series prediction function. \n")
higher_team_abb = input("Input an abbreviation for the higher seeded team (i.e. 'BOS', 'ATL', 'BKN', etc): ")
lower_team_abb = input("Input an abbreviation for the lower seeded team (i.e. 'BOS', 'ATL', 'BKN', etc): ")
how_many_won_higher = int(input("Input how many games in the series the higher seed has already won (i.e. 0-4): "))
how_many_won_lower = int(input("Input how many games in the series the lower seed has already won (i.e. 0-4): "))
days_from_today = int(input("Input how many days from today the first game will be on (i.e. 0-30 - this is to approximate and account for the proper injury projections): "))


now.predict_series(higher_seed_abb=higher_team_abb, lower_seed_abb=lower_team_abb, 
                   higher_already_won=how_many_won_higher, lower_already_won=how_many_won_lower,
                   for_simulation = False, series_starts_in_how_many_games=days_from_today)


# test playoff simulate from this point (FUNCTION 3)

print("\nNow we test the playoff simulation from today on. Make sure that results look up to date to current playoffs! \n")
now.simulate_playoffs_from_this_point()

# test round probabilities from this point (FUNCTION 4)

print("\n Now we test the playoff round win probabilities for each team from today on. Make sure that results look up to date to current playoffs! \n")
now.get_probs_of_each_round()

# if 

# If all of the above works, we are ready to start the command line interface
# use the instructions at this link https://www.digitalocean.com/community/tutorials/how-to-use-argparse-to-write-command-line-programs-in-python
# use the commands in the read me to map to the functions above
# then we are done with functionality stuff just have to write tests and pass style convention tests.
