"""Create and train PyTorch NBA model"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import pull
import itertools

# Pull feature data:

train_class = training_dataset(since = 2000) # Feel free to change training year start


# Load training dataset with linspace of hyperparameters for injury_adjusted and avg_minutes_played_cutoff:

# Note 1: Features represent summary statistics for player averages on each team roster ("_H" and "_A") for
#         variables 'PTS', 'FGM', 'FGA', 'FG_PCT', 'FG3M', 'FG3A', 'FG3_PCT', 'FTM', 'FTA', 'FT_PCT', 'OREB', 'DREB',
#         'REB', 'AST', 'STL', 'BLK', and 'TOV'. Summary statistics are only inclusive of players that average 
#         equal or more than avg_minutes_played_cutoff minutes per game. Finally, if injury_adjusted is True
#         than players that are or were injured during game time are also dicluded from such summary statistics.
#         Each feature is formatted "{summary statistic}_{variable}_{H/A}" (i.e. "mean_AST_H")

possible_injury_adjusted = [True, False]
possible_avg_minutes_played_cutoff = list(range(0, 30, 3))
hyperparamter_space = list(itertools.product(possible_injury_adjusted, possible_avg_minutes_played_cutoff))

# Load all possible hyperparameter datasets
for settings in hyperparamter_space:
    train_class.load_train_data(injury_adjusted=settings[0], avg_minutes_played_cutoff=settings[1])

# Create model archetecture and attempt to train on each of the above datasets to see which has best cross validated test AUC...

# Note: To access each of the above loaded training sets: 

# train_set_1 = train_class.get_training_dataset(injury_adjusted=True, avg_minutes_played_cutoff=20, force_update=False)


# Create and train the NBA model

class NBA_Model(nn.Module):
    def __init__(self):
        super().__init__()

    def forward(self, x):
        pass
