#### BIOSTAT 821 Final Project

# NBA Playoff Outcome Predictor

## For Users:

This project is a Python-based NBA playoff outcome predictor that utilizes machine learning to predict game outcomes and playoff picture results. It features a command line interface that users can install and use to create inquiries for games and playoffs.

A quick note: all data updates happen in real time, and rerunning requests will change as the NBA landscape changes throughout the playoffs. All data aquisition is done through NBA API, and real time cleaning and updates are done in objects/year.py as well as objects/current_state.py.

### Installation

To use the predictor, you must have Python 3.6 or higher installed. First, clone the repository to your local machine and install requirements. Also set your PYTHONPATH appropriately if neccecary:

```
git clone https://github.com/wpowell31/biostats-821-final-project
export PYTHONPATH="{INSERT PATH TO CLONED REPO"}"
pip install -r requirements.txt
```

### Main Functionality

The command line interface includes four main commands:

**1. Predict Theoretical Playoff Game**
```
python3 cli/interface.py --predict_matchup
```

The interface will prompt the user for (1) the abbreviation of the home team, (2) the abbreviation of the away team, and (3) how many days from today the game will be played in.

Output will look like the following:

```
"BOS has a 77.53 chance of beating ATL at home."
```

**2. Predict Theoretical Playoff Series**
```
python3 cli/interface.py --predict_series
```

The interface will prompt the user for (1) the abbreviation of the higher seed, (2) the abbreviation of the lower seed, (3) how many games the higer seed has already won, (4) how many games the lower seed has already won, and (5) how many days from today the next game of the series will be played in. Each round winning probabilities will be output for both teams.

Output will look like the following:

```
BOS-ATL series is currently 0-0 

        BOS wins in 4: 15.99%
        BOS wins in 5: 30.47%
        BOS wins in 6: 17.69%
        BOS wins in 7: 19.14%
        ATL wins in 4: 1.18%
        ATL wins in 5: 2.4%
        ATL wins in 6: 7.59%
        ATL wins in 7: 5.55%
__________Total Probabilities__________
        BOS wins series: 83.28%
        ATL wins series: 16.72%
```

**3. True Playoff Simulator**
```
python3 cli/interface.py --simulate_playoffs_from_this_point
```

Simulates playoff situation from this CURRENT point in the season, accounting for injury projections. Updates each time you call the function.

Output will look like the following:

```
_____Pre-Playoffs_____
Updating playoff game data.
MIL secures 1 seed in the EAST with probability 100.0
BOS secures 2 seed in the EAST with probability 100.0
PHI secures 3 seed in the EAST with probability 100.0
CLE secures 4 seed in the EAST with probability 100.0
NYK secures 5 seed in the EAST with probability 100.0
BKN secures 6 seed in the EAST with probability 100.0
ATL secures 7 seed in the EAST with probability 100.0
MIA secures 8 seed in the EAST with probability 100.0
...
_____ROUND 1 SIMULATION_____
MIA wins MIA-MIL in 7 with probability 68.59% (Currently 2-1 MIA)
BOS wins BOS-ATL in 5 with probability 97.56% (Currently 3-1 BOS)
PHI wins PHI-BKN in 4 with probability 100% (Currently 4-0 PHI)
NYK wins NYK-CLE in 6 with probability 72.36% (Currently 3-1 NYK)
DEN wins DEN-MIN in 5 with probability 97.56% (Currently 3-1 DEN)
LAL wins LAL-MEM in 5 with probability 67.3% (Currently 2-1 LAL)
GSW wins GSW-SAC in 6 with probability 39.29% (Currently 2-2 GSW)
PHX wins PHX-LAC in 6 with probability 96.48% (Currently 3-1 PHX)
_____ROUND 2 SIMULATION_____
MIA wins MIA-NYK in 7 with probability 37.2%
BOS wins BOS-PHI in 6 with probability 66.82%
DEN wins DEN-PHX in 6 with probability 88.51%
...
```

**4. True Playoff Round Probability Calculator**
```
python3 cli/interface.py --get_probs_of_each_round
```

Calculates each teams CURRENT probability of winning each round of NBA playoffs based on regular season features. Does so throigh conditional and cumulative probability calculation as opposed to bootstrapping for faster results. Updates each time you call the function.

Output will look like the following:

```
Loading R1 win probabilities...
MIL-MIA is currently in progress 1-2
BOS-ATL is currently in progress 3-1
PHI-BKN series was completed 4-0
CLE-NYK is currently in progress 1-3
DEN-MIN is currently in progress 3-1
MEM-LAL is currently in progress 1-2
SAC-GSW is currently in progress 2-2
PHX-LAC is currently in progress 3-1
_______ROUND 1________
PHI wins: 100%
DEN wins: 97.56%
BOS wins: 97.56%
PHX wins: 96.48%
NYK wins: 72.36%
MIA wins: 68.59%
LAL wins: 67.3%
SAC wins: 60.71%
GSW wins: 39.29%
MEM wins: 32.7%
MIL wins: 31.41%
CLE wins: 27.64%
LAC wins: 3.52%
ATL wins: 2.44%
MIN wins: 2.44%
BKN wins: 0%

Loading R2 win probabilities...
_______ROUND 2________
DEN wins: 86.2%
BOS wins: 65.63%
LAL wins: 45.5%
MIA wins: 39.67%
PHI wins: 32.39%
NYK wins: 28.05%
MIL wins: 21.49%
MEM wins: 20.63%
SAC wins: 19.67%
GSW wins: 14.21%
PHX wins: 11.29%
CLE wins: 10.79%
ATL wins: 1.98%
MIN wins: 1.93%
LAC wins: 0.58%
BKN wins: 0.0%

Loading R3 win probabilities...
_______ROUND 3________
DEN wins: 69.05%
BOS wins: 26.47%
MIA wins: 22.17%
NYK wins: 17.49%
MIL wins: 13.39%
PHI wins: 12.64%
LAL wins: 8.83%
PHX wins: 8.45%
CLE wins: 7.43%
MEM wins: 5.62%
SAC wins: 3.51%
GSW wins: 2.84%
MIN wins: 1.31%
ATL wins: 0.41%
LAC wins: 0.4%
BKN wins: 0.0%
```



### Help Functions

**1. Model Reload**

```
python3 cli/interface.py --model_retrain
```

The model included with the cloned reposity was trained on data from 2000 to 2021. If years have passed and you would like to update the model simply run this command and the model will be retrained with injury corrective and player hyperparameter tuning (see below section). You will be asked if you truly want to do this, as it may take more than 40 minutes to collect features and train the model.

## How does modeling account for injuries?

The average number of minutes of the player that is out for injury or other reasons is calculated and distributed to the most qualified players of the same position up to certain thresholds until all minutes lost have been reaccounted for. The players minute-dependent statistics (i.e. PTS, REBOUNDS, etc) are then recalculated accordingly. Note that our injury adjustments assume linearity of statistics by each minute added to their play time. Additionally, only players that average 25 minutes or more are injury adjusted for.

## For Developers:

**Objects and functions are each stored in their own files in the objects/ directory. Below is a description of each.**

**year(season : int)**:** Object to update data a given season in real time. Contains properties and calls methods for feature extraction for that year as well as injury adjustments.

**model_reload():** Function to reload and train model up to current year whenever called

**training_dataset(since : int):** Stores datasets that can be updated for training model. Takes in "since" which is an indicator of when model training data should start (it ends the two years prior to the current year).

**XGBoostModel(injury_adjusted : bool, avg_minutes_played_cutoff : int, train_class : training_dataset):** (Stored in objects/model) contains class for xgboost classifier used for prediction. Takes in training dataset hyperparameters "injury_adjusted" to indicate whether features should be injury adjusted, and "avg_minutes_played_cutoff" to indicate how many minutes a player needs to play on average to contrinute to features. Also takes in a training_dataset object.

**current_state():** Class that organizes and regularly updates all data from current year so that features can be made and predicitons are updated. Also contains methods for calculating round probabilities via conditional probability calculations.

There are also various helper functions contained in objects/helper.py that simply aid in the creation of the above obejcts through scrapers and other useful things.

**Data is included in the data folder, below is a description.**

**data/best_playoff_model.pickle**: A pickle file containing the pretrained XGBoost model discussed earlier. THis can be updated any time with model_reload.

**data/current_state_object**: A pickle file containing a current_state object . This allows the user to not have to download the current year data each time, and the object itself is self-updating.

**Command line interface object is contained in cli/interface.py**

It is produced with the argparse library.

## Testing

To run test files, simply run...
```
python3 -m unittest tests/{insert test file}.py
```

## Credits

This project was created by Will Powell, Nick Bachelder, and Wanying Mo. Main game and box data is pulled from NBA API. All current injuries are calculated by pulling from the CBS website. Since we do not calculate the probability of making the playoff, such probabilities are pulled from NBA references predictions.
