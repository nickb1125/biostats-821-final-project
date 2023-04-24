"""Define XGBoost model class:"""
import xgboost as xgb
from sklearn.model_selection import GridSearchCV

class XGBoostModel:
    def __init__(self, injury_adjusted, avg_minutes_played_cutoff, train_class):
        self.injury_adjusted = injury_adjusted
        self.avg_minutes_played_cutoff = avg_minutes_played_cutoff
        self.train_set = train_class.get_training_dataset(
            injury_adjusted=self.injury_adjusted,
            avg_minutes_played_cutoff=self.avg_minutes_played_cutoff,
            force_update=False,
        )
        self.model = None
        self.best_params = None
        self.best_score = None

    def grid_search(self, param_grid):
        xgb_clf = xgb.XGBClassifier(objective="binary:logistic", n_jobs=-1)
        grid_search = GridSearchCV(
            estimator=xgb_clf, param_grid=param_grid, scoring="roc_auc", cv=5, verbose=0
        )
        y = self.train_set["HOME_WIN"]
        X = self.train_set.drop("HOME_WIN", axis=1)

        grid_search.fit(X, y)
        self.model = grid_search.best_estimator_
        self.best_params = grid_search.best_params_
        self.best_score = grid_search.best_score_