# biostats-821-final-project

# NBA Playoff Outcome Predictor

This project is a Python-based NBA playoff outcome predictor that utilizes machine learning to predict game outcomes and playoff picture. It includes a data API that pulls data from the NBA, a model that predicts playoff outcomes given a list of features, and a command line interface that users can install and use to create inquiries for games and playoffs.

The project includes two main functions:

1. predict_game(home_team_abb, away_team_abb) - predicts the outcome of a single game based on input data.
2. predict_playoff_picture() - returns the ordered probabilities of each team making the NBA finals and previous rounds of the playoffs.

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

Teams likely to make the NBA finals:
1. LAL - 35%
2. BOS - 30%
3. HOU - 25%
4. MIL - 10%

Teams likely to make the Conference Finals:
1. LAL - 80%
2. HOU - 70%
3. BOS - 60%
4. MIL - 50%
5. MIA - 20%
6. PHI - 10%
7. DEN - 5%
8. TOR - 5%

### Model

The model used in this project is a multilayer-perceptron trained on historical NBA playoff data. The model uses features such as average point differential, ELO, and team statistics to predict the outcome of playoff games. 

### Credits

This project was created by Will Powell, Nick Bachelder, and Wanying Mo. It is based on the NBA-API and uses data from Basketball Reference.
