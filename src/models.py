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

# Pull feature data:

#train_class = training_dataset(since = 2020) # Feel free to change training year start


# Load training dataset with linspace of hyperparameters for injury_adjusted and avg_minutes_played_cutoff:

# Note 1: Features represent summary statistics for player averages on each team roster ("_H" and "_A") for
#         variables 'PTS', 'FGM', 'FGA', 'FG_PCT', 'FG3M', 'FG3A', 'FG3_PCT', 'FTM', 'FTA', 'FT_PCT', 'OREB', 'DREB',
#         'REB', 'AST', 'STL', 'BLK', and 'TOV'. Summary statistics are only inclusive of players that average 
#         equal or more than avg_minutes_played_cutoff minutes per game. Finally, if injury_adjusted is True
#         than players that are or were injured during game time are also dicluded from such summary statistics.
#         Each feature is formatted "{summary statistic}_{variable}_{H/A}" (i.e. "mean_AST_H")

possible_injury_adjusted = [True, False]
possible_avg_minutes_played_cutoff = list(range(0, 10, 5))
hyperparamter_space = list(itertools.product(possible_injury_adjusted, possible_avg_minutes_played_cutoff))

# Load all possible hyperparameter datasets
#for settings in hyperparamter_space:
 #   train_class.load_train_data(injury_adjusted=settings[0], avg_minutes_played_cutoff=settings[1])

# Create model archetecture and attempt to train on each of the above datasets to see which has best cross validated test AUC...

# Note: To access each of the above loaded training sets: 

#train_set_1 = train_class.get_training_dataset(injury_adjusted=True, avg_minutes_played_cutoff=10, force_update=False)
#print(train_set_1.shape)

# Save train_class using pickle
#import pickle
#with open('train_class.pkl', 'wb') as f:
#    pickle.dump(train_class, f)


# Get train_class from saved pickle object
#fileObj = open('train_class_test.pkl', 'rb')
#train_class = pickle.load(fileObj)
#fileObj.close()

# Create and train the NBA model

# Pull feature data:
#train_class = training_dataset(since = 2020) # Feel free to change training year start

# Define XGBoost model class:
class XGBoostModel:
    def __init__(self, injury_adjusted, avg_minutes_played_cutoff):
        self.injury_adjusted = injury_adjusted
        self.avg_minutes_played_cutoff = avg_minutes_played_cutoff
        self.train_set = train_class.get_training_dataset(
            injury_adjusted=self.injury_adjusted, 
            avg_minutes_played_cutoff=self.avg_minutes_played_cutoff, 
            force_update=False
        )
        self.model = None
        self.best_params = None
        self.best_score = None
        
    def grid_search(self, param_grid):
        xgb_clf = xgb.XGBClassifier(objective='binary:logistic', n_jobs=-1)
        grid_search = GridSearchCV(
            estimator=xgb_clf,
            param_grid=param_grid,
            scoring='roc_auc',
            cv=2,
            verbose=0
        )
        y = self.train_set['HOME_WIN']
        X = self.train_set.drop('HOME_WIN', axis=1)

        grid_search.fit(X, y)
        self.model = grid_search.best_estimator_
        self.best_params = grid_search.best_params_
        self.best_score = grid_search.best_score_
        
# Define hyperparameter space:

hyperparameter_space = {
    'max_depth': [3, 5],
    'learning_rate': [0.01, 0.1],
    'n_estimators': [100, 200],
    'min_child_weight': [1, 3],
    'gamma': [0, 0.1]
}

print('----->testing single False, 5 test')
test_xgb_model = XGBoostModel(False, 5)
test_xgb_model.grid_search(param_grid=hyperparameter_space)
print(test_xgb_model.best_params)
print(test_xgb_model.model)
print(test_xgb_model.best_score)


print('----->testing all possible cominations now')
# Load all possible hyperparameter datasets and perform grid search:
models = []
for settings in itertools.product(possible_injury_adjusted, possible_avg_minutes_played_cutoff):
    print(f"--------> Searching for injury adjusted {settings[0]}, minutes cutoff {settings[1]}")
    xgb_model = XGBoostModel(injury_adjusted=settings[0], avg_minutes_played_cutoff=settings[1])
    xgb_model.grid_search(param_grid=hyperparameter_space)
    models.append(xgb_model)
    print(xgb_model.best_score)
    
# Find model with best cross validated test AUC:

best_model = max(models, key=lambda model: model.model.best_score)
print('Best hyperparameters:', best_model.best_params)
print('Best score', best_model.best_score)
print(best_model.injury_adjusted, best_model.avg_minutes_played_cutoff)



