# biostats-821-final-project

# NBA Playoff Outcome Predictor

This project is a Python-based NBA playoff outcome predictor that utilizes machine learning to predict game outcomes and playoff picture. It includes a data API that pulls data from the NBA, a model that predicts playoff outcomes given a list of features, and a command line interface that users can install and use to create inquiries for games and playoffs.

The project includes two main functions:

1. predict_game(home_team_abb, away_team_abb) - predicts the outcome of a single game based on input data.
2. predict_playoff_picture() - returns the ordered probabilities of each team making the NBA finals and previous rounds of the playoffs.
3. simulate_playoffs_from_this_point() - simulates the playoffs given what has already happened this year (if anything)

### Installation

To use the predictor, you must have Python 3.6 or higher installed. First, clone the repository to your local machine:

git clone https://github.com/wpowell31/biostats-821-final-project
pip install -r requirements.txt

### Usage

The predict_game() function takes two arguments - the home team abbreviation and the away team abbreviation. For example:

from predictor import predict_game
predict_game("LAL", "MIA") -> Predicted winner: LAL at 68%

The predict_playoff_picture() function returns the ordered probabilities of each team making the NBA finals and previous rounds of the playoffs. For example:

from predictor import predict_playoff_picture
predict_playoff_picture()

| Team | Finals | Conference Finals | Conference Semifinals | First Round |
| --- | --- | --- | --- | --- |
| Brooklyn Nets | 30% | 60% | 80% | 95% |
| Los Angeles Lakers | 25% | 55% | 75% | 90% |
| Utah Jazz | 20% | 50% | 70% | 85% |
| Milwaukee Bucks | 15% | 45% | 65% | 80% |
| Philadelphia 76ers | 10% | 40% | 60% | 75% |
| Phoenix Suns | 5% | 35% | 55% | 70% |
| Denver Nuggets | 5% | 30% | 50% | 65% |
| Miami Heat | 4% | 25% | 45% | 60% |

The simulate_playoffs_from_this_point() function returns a simulation of the playoff picture:


"First Round:

Eastern Conference:

(1) Philadelphia 76ers vs. (8) Charlotte Hornets

The 76ers win the series 4-1.

(4) New York Knicks vs. (5) Atlanta Hawks

The Knicks win the series 4-3 in a close matchup.

(3) Milwaukee Bucks vs. (6) Miami Heat

The Bucks win the series 4-2.

(2) Brooklyn Nets vs. (7) Boston Celtics

The Nets win the series 4-0, sweeping the Celtics.

Western Conference:

(1) Utah Jazz vs. (8) Golden State Warriors"

.... so on


### API

The api.py file contains a Flask app that serves as the data API. It exposes two endpoints:

/teams - returns a list of all NBA teams and their abbreviations.
/team/<team_abb> - returns CURRENT model features (including features not included through NBA API like ELO).
To run the API, navigate to the project directory and run:

python api.py

The API will be hosted on http://localhost:5000.

### Model

The model used in this project is a multilayer-perceptron trained on historical NBA playoff data. The model uses features such as average point differential, ELO, and team statistics to predict the outcome of playoff games. 

### Credits

This project was created by Will Powell, Nick Bachelder, and Wanying Mo. It is based on the NBA-API and uses data from Basketball Reference.
