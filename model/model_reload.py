"""Create and train PyTorch NBA model"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import sys
import pull
from pull import training_dataset, year
import itertools
import pandas as pd
import itertools
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import GridSearchCV
import pickle
import os

# Ask if user wants to update model:

if (os.path.exists("data/train_class.pickle")) & (os.path.exists("data/best_playoff_model.pickle")):
    with open('data/train_class.pickle', 'rb') as handle:
        train_class = pickle.load(handle)
    with open('data/best_playoff_model.pickle', 'rb') as handle:
        best_playoff_model = pickle.load(handle)
    while True:
        update_model = input(f"---Currently existing model is trained up to {train_class.since} and has a cross validated test AUC of {best_playoff_model.best_score}.--- \n \n---The current model is trained with settings INJURY_ADJUST = {best_playoff_model.injury_adjusted} and AVG_MIN_PLAYED_CUTOFF = {best_playoff_model.avg_minutes_played_cutoff}.--- \n \n---Note that some of the best nba playoff models range in AUC from 0.58 to 0.62 on average.---\n \n-------------->'Yes' OR 'No': DO YOU WANT TO UPDATE THE CURRENTLY TRAINED MODEL? (THIS WILL TAKE MORE THAN 45 MINUTES): ")
        if update_model == "Yes" or update_model == "No":
            break
        print("Invalid input. Must be 'Yes' or 'No'. Please try again.")
    if update_model == "Yes":
        update_model = True
    else:
        update_model = False
else:
    print("There exists no pretrained playoff model. Must pull data and train model. This will take ~45 minutes.")
    update_model = True

# Pull feature data:

if not update_model:
    exit()

train_class = training_dataset(since = 2000) # Feel free to change training year start
# Load training dataset with linspace of hyperparameters for injury_adjusted and avg_minutes_played_cutoff:
# Note 1: Features represent summary statistics for player averages on each team roster ("_H" and "_A") for
#         variables 'PTS', 'FGM', 'FGA', 'FG_PCT', 'FG3M', 'FG3A', 'FG3_PCT', 'FTM', 'FTA', 'FT_PCT', 'OREB', 'DREB',
#         'REB', 'AST', 'STL', 'BLK', and 'TOV'. Summary statistics are only inclusive of players that average 
#         equal or more than avg_minutes_played_cutoff minutes per game. Finally, if injury_adjusted is True
#         than players that are or were injured during game time are also dicluded from such summary statistics.
#         Each feature is formatted "{summary statistic}_{variable}_{H/A}" (i.e. "mean_AST_H")
possible_injury_adjusted = [True, False]
possible_avg_minutes_played_cutoff = list(range(0, 15, 5))
hyperparamter_space = list(itertools.product(possible_injury_adjusted, possible_avg_minutes_played_cutoff))
# Load all possible hyperparameter datasets
for settings in hyperparamter_space:
    train_class.load_train_data(injury_adjusted=settings[0], avg_minutes_played_cutoff=settings[1])
# Save train_class using pickle
with open('data/train_class.pickle', 'wb') as handle:
    pickle.dump(train_class, handle, protocol=pickle.HIGHEST_PROTOCOL)

# Create and train the NBA model
# Define hyperparameter space:

hyperparameter_space = {
    'max_depth': [3, 5, 7],
    'learning_rate': [0.001,0.01, 0.1],
    'n_estimators': [100, 200],
    'min_child_weight': [1, 3],
    'gamma': [0, 0.1]
}

print('----->testing all possible cominations now')
# Load all possible hyperparameter datasets and perform grid search:
models = []
for settings in itertools.product(possible_injury_adjusted, possible_avg_minutes_played_cutoff):
    print(f"-------->Searching for injury adjusted {settings[0]}, minutes cutoff {settings[1]}")
    xgb_model = XGBoostModel(injury_adjusted=settings[0], avg_minutes_played_cutoff=settings[1])
    xgb_model.grid_search(param_grid=hyperparameter_space)
    models.append(xgb_model)
    print(f"Best AUC with cross validated hyperparameters: {xgb_model.best_score}")

print('Best hyperparameters:', best_playoff_model.model.get_params)
print('Best AUC score', best_playoff_model.best_score)
print(best_playoff_model.injury_adjusted, best_playoff_model.avg_minutes_played_cutoff)
    
# Find model with best cross validated test AUC:

print('Best XGB hyperparameters:', best_playoff_model.model.get_params)
print('Best AUC score', best_playoff_model.best_score)
print(f"Best training hyperparameters are INJURY_ADJUST = {best_playoff_model.injury_adjusted}, AVG_MIN_CUTOFF = {best_playoff_model.avg_minutes_played_cutoff}")

# Save model

with open('data/best_playoff_model.pickle', 'wb') as handle:
    pickle.dump(best_model, handle, protocol=pickle.HIGHEST_PROTOCOL)