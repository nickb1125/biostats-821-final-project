"""Current state class."""

import datetime
import pickle
from objects.year import year
from objects.helper import team_abb_to_id, scrape_current_nba_injuries, scrape_nba_playoff_projections, team_id_to_abb_conv
import numpy as np
import itertools
import pandas as pd
from random import choices

class current_state:
    def __init__(self):
        if datetime.datetime.now().month <= 8:
            self.year = datetime.datetime.now().year - 1
        else:
            self.year = datetime.datetime.now().year
        self.created_on = datetime.datetime.now()
        self.year_class = {}
        with open("data/best_playoff_model.pickle", "rb") as handle:
            self.model = pickle.load(handle)
        loader_year_class = self.get_current_year_class
        self.script = {
            "R1": [
                ("1_EAST", "8_EAST"),
                ("2_EAST", "7_EAST"),
                ("3_EAST", "6_EAST"),
                ("4_EAST", "5_EAST"),
                ("1_WEST", "8_WEST"),
                ("2_WEST", "7_WEST"),
                ("3_WEST", "6_WEST"),
                ("4_WEST", "5_WEST"),
            ],
            "R2": [
                ("1_EAST_8_EAST", "4_EAST_5_EAST"),
                ("2_EAST_7_EAST", "3_EAST_6_EAST"),
                ("1_WEST_8_WEST", "4_WEST_5_WEST"),
                ("2_WEST_7_WEST", "3_WEST_6_WEST"),
            ],
            "R3": [
                ("1_EAST_8_EAST_4_EAST_5_EAST", "2_EAST_7_EAST_3_EAST_6_EAST"),
                ("1_WEST_8_WEST_4_WEST_5_WEST", "2_WEST_7_WEST_3_WEST_6_WEST"),
            ],
            "R4": [
                (
                    "1_EAST_8_EAST_4_EAST_5_EAST_2_EAST_7_EAST_3_EAST_6_EAST",
                    "1_WEST_8_WEST_4_WEST_5_WEST_2_WEST_7_WEST_3_WEST_6_WEST",
                )
            ],
        }

    def print_current_team_injuries(self, team_id, games_ahead_of_today):
        """Prints current team injuries"""
        all_injuries = scrape_current_nba_injuries(games_ahead_of_today)
        this_year = self.get_current_year_class.get("current")
        players_this_team = (
            this_year.roster_info.query("TEAM_ID == @team_id")
            .reset_index(drop=1)
            .PLAYER_ID
        )
        injured_players = (
            all_injuries.query("PLAYER_ID in @players_this_team")
            .reset_index(drop=1)
            .PLAYER_NAME.tolist()
        )
        return injured_players

    def get_current_max_playoff_seed_probs(self):
        """Gets teams with max probability of each seed in tourney."""
        seeds = self.get_playoff_picture_liklihood()
        ret = dict()
        for team_abb, seed_dict in seeds.items():
            team_seeds = []
            team_probs = []
            for seed, prob in seed_dict.items():
                team_seeds.append(seed)
                team_probs.append(prob)
            if np.sum(team_probs) == 0:
                continue
            seed_choice = team_seeds[team_probs.index(max(team_probs))]
            with_prob = seed_dict[seed_choice]
            seed_choice = seed_choice.replace("_SEED", "")
            ret.update({seed_choice: {team_abb: with_prob}})
        return ret

    def get_base_seeds(self):
        """Gets base seeds for simulation"""
        current_round_state = self.get_current_max_playoff_seed_probs()
        seeds = []
        for key, this_dict in current_round_state.items():
            this_seed = pd.DataFrame({"SEED": [key]})
            for team_abb, prob in this_dict.items():
                this_seed["TEAM_ABB"] = team_abb
            seeds.append(this_seed)
        seeds = pd.concat(seeds)
        return seeds

    def get_current_tourney_state(self):
        """Gets the state of the tournement currently. If hasnt started just gets max seed probs."""
        seeds = self.get_base_seeds()
        this_year = self.year_class.get("current")
        games_thus_far = this_year.playoff_game_data[
            ["TEAM_ABBREVIATION_H", "TEAM_ABBREVIATION_A", "OUTCOME"]
        ].copy()
        games_thus_far = (
            games_thus_far.merge(
                seeds, left_on="TEAM_ABBREVIATION_H", right_on="TEAM_ABB", how = "left"
            )
            .rename(columns={"SEED": "SEED_H"})
            .drop(["TEAM_ABB"], axis=1)
            .merge(seeds, left_on="TEAM_ABBREVIATION_A", right_on="TEAM_ABB", how = "left")
            .rename(columns={"SEED": "SEED_A"})
            .drop(["TEAM_ABB"], axis=1)
            .copy()
        )
        games_thus_far["WINNER"] = [
            row.TEAM_ABBREVIATION_H if row.OUTCOME == 1 else row.TEAM_ABBREVIATION_A
            for _, row in games_thus_far.iterrows()
        ]
        got_this_far = True
        current_round_state = {"R0": self.get_current_max_playoff_seed_probs()}
        for round in ["R1", "R2", "R3", "R4"]:
            matchups = self.script[round]
            current_round_state.update({round: dict()})
            for matchup in matchups:
                if round == "R1":
                    games_in_this_matchup = games_thus_far.query(
                        "(SEED_H == @matchup[0] & SEED_A == @matchup[1]) or (SEED_H == @matchup[1] & SEED_A == @matchup[0])"
                    ).copy()
                    team_1_abb = games_in_this_matchup.TEAM_ABBREVIATION_H.unique()[0]
                    team_2_abb = games_in_this_matchup.TEAM_ABBREVIATION_A.unique()[0]
                else:
                    previous_round = current_round_state["R" + str(int(round[1]) - 1)]
                    team_1_abb = [k for k, v in previous_round[matchup[0]].items() if v == 4][0]
                    team_2_abb = [k for k, v in previous_round[matchup[1]].items() if v == 4][0]
                    games_in_this_matchup = games_thus_far.query(
                        "(TEAM_ABBREVIATION_H == @team_1_abb & TEAM_ABBREVIATION_A == @team_2_abb) or (TEAM_ABBREVIATION_H == @team_2_abb & TEAM_ABBREVIATION_H == @team_1_abb)"
                    ).copy()
                matchup_status = dict(games_in_this_matchup.WINNER.value_counts())
                for team in [
                    team_1_abb,
                    team_2_abb,
                ]:
                    if team not in matchup_status.keys():
                        matchup_status.update({team: 0})
                current_round_state[round].update(
                    {f"{matchup[0]}_{matchup[1]}": matchup_status}
                )
                finished = False
                for key, value in matchup_status.items():
                    if value == 4:
                        finished = True
                        new_seed = pd.DataFrame(
                            {"SEED": [matchup[0] + "_" + matchup[1]], "TEAM_ABB": [key]}
                        )
                        seeds = pd.concat([seeds, new_seed])
                if not finished:
                    got_this_far = False
            if not got_this_far:
                break
        return current_round_state

    def get_playoff_picture_liklihood(self):
        """Gets all probabilities of seeds for tourney."""
        playoff_proj = scrape_nba_playoff_projections()
        west = playoff_proj["West"]
        east = playoff_proj["East"]
        seed_columns = [
            "1_SEED_PROB",
            "2_SEED_PROB",
            "3_SEED_PROB",
            "4_SEED_PROB",
            "5_SEED_PROB",
            "6_SEED_PROB",
            "7_SEED_PROB",
            "8_SEED_PROB",
        ]
        west[seed_columns] = west[seed_columns].applymap(float)
        east[seed_columns] = east[seed_columns].applymap(float)
        possible_seeds_dict = dict()
        for index, row in east.iterrows():
            team_id = team_id_to_abb_conv(row.TEAM_ID)
            possible_seeds_dict.update({team_id: dict()})
            for seed in range(1, 9):
                possible_seeds_dict[team_id].update(
                    {f"{seed}_EAST": row[f"{seed}_SEED_PROB"]}
                )
        for index, row in west.iterrows():
            team_id = team_id_to_abb_conv(row.TEAM_ID)
            possible_seeds_dict.update({team_id: dict()})
            for seed in range(1, 9):
                possible_seeds_dict[team_id].update(
                    {f"{seed}_WEST": row[f"{seed}_SEED_PROB"]}
                )
        return possible_seeds_dict

    @property
    def get_current_year_class(self):
        if len(self.year_class.keys()) == 0:
            self.year_class.update({"current": year(self.year)})
        return self.year_class

    def predict_matchup(self, home_abb, away_abb, games_ahead_of_today=0, for_simulation = True):
        """Predicts upcoming matchup."""
        home_id, away_id = team_abb_to_id(home_abb), team_abb_to_id(away_abb)
        features = self.year_class.get("current").get_features_for_upcoming(
            home_team=home_id,
            away_team=away_id,
            injury_adjusted=self.model.injury_adjusted,
            avg_minutes_played_cutoff=self.model.avg_minutes_played_cutoff,
            games_ahead_of_today=games_ahead_of_today,
        )
        prob = self.model.model.predict_proba(features)
        if not for_simulation:
            print(f"{home_abb} has a {round(prob[0][1] * 100, 2)} chance of beating {away_abb} at home.")
        return prob[0][1]  # Return home win probabilities

    def predict_series(
        self,
        higher_seed_abb,
        lower_seed_abb,
        higher_already_won=0,
        lower_already_won=0,
        for_simulation=False,
        series_starts_in_how_many_games=0,
    ):
        """Get probabilities of each team winning in games 4-7 of the series."""
        if (higher_already_won > 4) or (lower_already_won > 4):
            return KeyError("A team cant win more than 4 games in a series")
        if higher_already_won == 4:
            if not for_simulation:
                print(
                        f"{higher_seed_abb} wins {higher_seed_abb}-{lower_seed_abb} in {higher_already_won + lower_already_won} with probability 100%"
                    )
            num_games = higher_already_won + lower_already_won
            return {higher_seed_abb: {num_games: 1}}
        if lower_already_won == 4:
            if not for_simulation:
                print(
                        f"{lower_seed_abb} wins {lower_seed_abb}-{higher_seed_abb} in {higher_already_won + lower_already_won} with probability 100%"
                    )
            num_games = higher_already_won + lower_already_won
            return {lower_seed_abb: {num_games: 1}}
        prob_game_1 = self.predict_matchup(
            home_abb=higher_seed_abb,
            away_abb=lower_seed_abb,
            games_ahead_of_today=series_starts_in_how_many_games,
        )
        prob_game_2 = self.predict_matchup(
            home_abb=higher_seed_abb,
            away_abb=lower_seed_abb,
            games_ahead_of_today=series_starts_in_how_many_games + 1,
        )
        prob_game_3 = self.predict_matchup(
            home_abb=lower_seed_abb,
            away_abb=higher_seed_abb,
            games_ahead_of_today=series_starts_in_how_many_games + 2,
        )
        prob_game_4 = self.predict_matchup(
            home_abb=lower_seed_abb,
            away_abb=higher_seed_abb,
            games_ahead_of_today=series_starts_in_how_many_games + 3,
        )
        prob_game_5 = self.predict_matchup(
            home_abb=higher_seed_abb,
            away_abb=lower_seed_abb,
            games_ahead_of_today=series_starts_in_how_many_games + 4,
        )
        prob_game_6 = self.predict_matchup(
            home_abb=lower_seed_abb,
            away_abb=higher_seed_abb,
            games_ahead_of_today=series_starts_in_how_many_games + 5,
        )
        prob_game_7 = self.predict_matchup(
            home_abb=higher_seed_abb,
            away_abb=lower_seed_abb,
            games_ahead_of_today=series_starts_in_how_many_games + 6,
        )
        if not for_simulation:
            higher_id, lower_id = team_abb_to_id(higher_seed_abb), team_abb_to_id(
                lower_seed_abb
            )
            print(
                "Accounting for the following injuries and appropriate return timetables..."
            )

            print(
                f"""Injured for {higher_seed_abb}: 
            \n --->Projected Game 1:{self.print_current_team_injuries(higher_id, games_ahead_of_today = series_starts_in_how_many_games)}
            \n --->Projected Game 2:{self.print_current_team_injuries(higher_id, games_ahead_of_today = series_starts_in_how_many_games + 1)}
            \n --->Projected Game 3:{self.print_current_team_injuries(higher_id, games_ahead_of_today = series_starts_in_how_many_games + 2)}
            \n --->Projected Game 4:{self.print_current_team_injuries(higher_id, games_ahead_of_today = series_starts_in_how_many_games + 3)}
            \n --->Projected Game 5:{self.print_current_team_injuries(higher_id, games_ahead_of_today = series_starts_in_how_many_games + 4)}
            \n --->Projected Game 6:{self.print_current_team_injuries(higher_id, games_ahead_of_today = series_starts_in_how_many_games + 5)}
            \n --->Projected Game 7:{self.print_current_team_injuries(higher_id, games_ahead_of_today = series_starts_in_how_many_games + 6)} \n"""
            )

            print(
                f"""Injured for {lower_seed_abb}: 
            \n --->Projected Game 1:{self.print_current_team_injuries(lower_id, games_ahead_of_today = series_starts_in_how_many_games)}
            \n --->Projected Game 2:{self.print_current_team_injuries(lower_id, games_ahead_of_today = series_starts_in_how_many_games + 1)}
            \n --->Projected Game 3:{self.print_current_team_injuries(lower_id, games_ahead_of_today = series_starts_in_how_many_games + 2)}
            \n --->Projected Game 4:{self.print_current_team_injuries(lower_id, games_ahead_of_today = series_starts_in_how_many_games + 3)}
            \n --->Projected Game 5:{self.print_current_team_injuries(lower_id, games_ahead_of_today = series_starts_in_how_many_games + 4)}
            \n --->Projected Game 6:{self.print_current_team_injuries(lower_id, games_ahead_of_today = series_starts_in_how_many_games + 5)}
            \n --->Projected Game 7:{self.print_current_team_injuries(lower_id, games_ahead_of_today = series_starts_in_how_many_games + 6)} \n"""
            )

            print(
                f"{higher_seed_abb}-{lower_seed_abb} series is currently {higher_already_won}-{lower_already_won} \n"
            )
        prob_higher_wins_each_game = (
            prob_game_1,
            prob_game_2,
            prob_game_3,
            prob_game_4,
            prob_game_5,
            prob_game_6,
            prob_game_7,
        )
        num_already_played = higher_already_won + lower_already_won
        already_occured = np.append(
            np.repeat(0, lower_already_won), np.repeat(1, higher_already_won)
        )
        prob_higher_wins_each_game = np.append(
            already_occured, prob_higher_wins_each_game[num_already_played:]
        )
        if num_already_played < 4:
            games_left_to_play = list(range(4, 8))
        else:
            games_left_to_play = list(range(num_already_played + 1, 8))
        # Get possible sample space
        sample_space_previously_over = []
        for game in games_left_to_play:
            sample_space_new = list(
                itertools.product([0, 1], repeat=game - num_already_played)
            )
            sample_space = [
                tuple(np.append(already_occured, outcome))
                for outcome in sample_space_new
            ]
            sample_space_without_previously_over = [
                outcome
                for outcome in sample_space
                if (outcome[: game - 1] not in sample_space_previously_over)
            ]
            ended_this_round = [
                outcome
                for outcome in sample_space_without_previously_over
                if ((outcome.count(1) == 4) and (outcome[-1] == 1))
                or ((outcome.count(0) == 4) and (outcome[-1] == 0))
            ]
            sample_space_previously_over.extend(ended_this_round)
        outcomes = {higher_seed_abb: dict(), lower_seed_abb: dict()}
        for outcome in sample_space_previously_over:
            num_games = len(outcome)
            higher_win_prob_list = prob_higher_wins_each_game[:num_games]
            prob_of_what_occured = np.product(
                list(
                    map(
                        lambda x, y: 1 - y if x == 0 else y,
                        outcome,
                        higher_win_prob_list,
                    )
                ),
                dtype=np.float64,
            )
            if outcome.count(1) == 4:
                if num_games in outcomes[higher_seed_abb].keys():
                    outcomes[higher_seed_abb][num_games].append(prob_of_what_occured)
                else:
                    outcomes[higher_seed_abb].update(
                        {num_games: [prob_of_what_occured]}
                    )
            elif outcome.count(0) == 4:
                if num_games in outcomes[lower_seed_abb].keys():
                    outcomes[lower_seed_abb][num_games].append(prob_of_what_occured)
                else:
                    outcomes[lower_seed_abb].update({num_games: [prob_of_what_occured]})
            else:
                raise KeyError("Proper number of wins was not obtained for either team")
        total_prob_higher, total_prob_lower = 0, 0
        for team_abb, value in outcomes.items():
            for inner_key, inner_value in value.items():
                prob = np.sum(inner_value)
                outcomes[team_abb][inner_key] = prob
                if not for_simulation:
                    print(
                        f"        {team_abb} wins in {inner_key}: {round(prob*100, 2)}%"
                    )
                if team_abb == higher_seed_abb:
                    total_prob_higher += prob
                else:
                    total_prob_lower += prob
        if not for_simulation:
            print("__________Total Probabilities__________")
            print(
                f"        {higher_seed_abb} wins series: {round(total_prob_higher*100, 2)}%"
            )
            print(
                f"        {lower_seed_abb} wins series: {round(total_prob_lower*100, 2)}%"
            )
        if for_simulation:
            return outcomes

    def simulate_playoffs_from_this_point(self):
        """Simulates playoffs."""
        print(f"Simulating {self.year} NBA-playoffs")
        print(f"_____Pre-Playoffs_____")
        current_state = self.get_current_tourney_state()
        for seed, dictio in current_state["R0"].items():
            for team, prob in dictio.items():
                print(
                    f"{team} secures {seed[0]} seed in the {seed[2:]} with probability {prob}"
                )
        current_round_num = max([int(key[1]) for key in current_state.keys()])
        base_seeds = self.get_base_seeds()
        seeds = base_seeds.copy()
        curr_year = self.year_class.get("current")
        rounds_to_play = list(range(1, 5))
        games_from_now = 0
        for this_round in rounds_to_play:
            round_str = f"R{this_round}"
            print(f"_____ROUND {this_round} SIMULATION_____")
            if (current_round_num >= this_round):
                current_round = current_state[f"R{this_round}"]
            else:
                current_round = dict()
            matchups_split = self.script[round_str]
            all_round_matchups = ["_".join(matchup) for matchup in matchups_split]
            matchups_not_shown = list(
                set(all_round_matchups) - set(current_round.keys())
            )
            for matchup in matchups_not_shown:
                match = [
                    match for match in matchups_split if "_".join(match) == matchup
                ][0]
                current_round.update(
                    {
                        matchup: {
                            seeds.query("SEED == @match[0]")
                            .reset_index(drop=1)
                            .TEAM_ABB[0]: 0,
                            seeds.query("SEED == @match[1]")
                            .reset_index(drop=1)
                            .TEAM_ABB[0]: 0,
                        }
                    }
                )
            # finish round by simulation
            for seed_reward, series_dict in current_round.items():
                both_teams = list(series_dict.keys())
                team_1, team_2 = both_teams[0], both_teams[1]
                team_1_already_won, team_2_already_won = (
                    series_dict[team_1],
                    series_dict[team_2],
                )
                team_1_seed = int(
                    base_seeds.query("TEAM_ABB == @team_1")
                    .reset_index(drop=1)
                    .SEED[0][0]
                )
                team_2_seed = int(
                    base_seeds.query("TEAM_ABB == @team_2")
                    .reset_index(drop=1)
                    .SEED[0][0]
                )
                if team_1_seed < team_2_seed:
                    probs_dict = self.predict_series(
                        higher_seed_abb=team_1,
                        lower_seed_abb=team_2,
                        higher_already_won=team_1_already_won,
                        lower_already_won=team_2_already_won,
                        for_simulation=True,
                    )
                elif team_1_seed > team_2_seed:
                    probs_dict = self.predict_series(
                        higher_seed_abb=team_2,
                        lower_seed_abb=team_1,
                        higher_already_won=team_2_already_won,
                        lower_already_won=team_1_already_won,
                        for_simulation=True,
                    )
                elif this_round == 4:
                    team_1_record, team_2_record = curr_year.get_team_record(
                        team_1
                    ), curr_year.get_team_record(team_2)
                    if team_1_record > team_2_record:
                        probs_dict = self.predict_series(
                            higher_seed_abb=team_1,
                            lower_seed_abb=team_2,
                            higher_already_won=team_1_already_won,
                            lower_already_won=team_2_already_won,
                            for_simulation=True,
                            series_starts_in_how_many_games=-(
                                team_1_already_won + team_2_already_won
                            ),
                        )
                    else:
                        probs_dict = self.predict_series(
                            higher_seed_abb=team_2,
                            lower_seed_abb=team_1,
                            higher_already_won=team_2_already_won,
                            lower_already_won=team_1_already_won,
                            for_simulation=True,
                            series_starts_in_how_many_games=-(
                                team_1_already_won + team_2_already_won
                            ),
                        )
                possible = []
                probs = []
                total_prob = dict()
                for team, game_dict in probs_dict.items():
                    total_prob.update({team: 0})
                    for game, prob in game_dict.items():
                        possible.append(
                            (
                                team,
                                game,
                            )
                        )
                        probs.append(prob)
                        total_prob[team] += prob
                occurs = choices(possible, probs)[0]
                if occurs[0] == team_1:
                    winner, loser = team_1, team_2
                else:
                    winner, loser = team_2, team_1
                if team_1_already_won > team_2_already_won:
                    if (team_1_already_won < 4) & (team_2_already_won < 4) & ((team_2_already_won != 0) & (team_1_already_won != 0)):
                        if_in_proj = f"(Currently {team_1_already_won}-{team_2_already_won} {team_1})"
                    else:
                        if_in_proj = ""
                    print(
                        f"{winner} wins {winner}-{loser} in {occurs[1]} with probability {round(total_prob[winner]*100, 2)}%" + if_in_proj
                    )
                else:
                    if (team_1_already_won < 4) & (team_2_already_won < 4) & ((team_2_already_won != 0) & (team_1_already_won != 0)):
                        if_in_proj = f"(Currently {team_2_already_won}-{team_1_already_won} {team_2})"
                    else:
                        if_in_proj = ""
                    print(
                        f"{winner} wins {winner}-{loser} in {occurs[1]} with probability {round(total_prob[winner]*100, 2)}%" + if_in_proj
                    )
                seeds = pd.concat(
                    [
                        seeds,
                        pd.DataFrame({"SEED": [seed_reward], "TEAM_ABB": [winner]}),
                    ]
                )
            if current_round_num == this_round:
                games_from_now = 3
            elif current_round_num > this_round:
                games_from_now = 0
            else:
                games_from_now += 7

    def get_probs_of_each_round(self):
        base_seeds = self.get_base_seeds()
        current_state = self.get_current_tourney_state()
        prob_of_seed = {row.SEED: {row.TEAM_ABB: 1} for _, row in base_seeds.iterrows()}
        for this_round, matchups in self.script.items():
            print(f"Loading {this_round} win probabilities...")
            if this_round not in current_state.keys():
                current_state.update({this_round: dict()})
            for matchup in matchups:
                seed_reward = "_".join(matchup)
                if this_round == "R4":
                    year_class = self.get_current_year_class.get("current")
                    team_1_record = year_class.get_team_record(matchup[0])
                    team_2_record = year_class.get_team_record(matchup[1])
                    if team_1_record > team_2_record:
                        higher_seed_probs = prob_of_seed[matchup[0]]
                        lower_seed_probs = prob_of_seed[matchup[1]]
                    else:
                        higher_seed_probs = prob_of_seed[matchup[1]]
                        lower_seed_probs = prob_of_seed[matchup[0]]
                else:
                    higher_seed_probs = prob_of_seed[matchup[0]]
                    lower_seed_probs = prob_of_seed[matchup[1]]
                prob_of_matchups_dict = {
                    f"{higher_seed_abb}_{lower_seed_abb}": higher_seed_probs[
                        higher_seed_abb
                    ]
                    * lower_seed_probs[lower_seed_abb]
                    for higher_seed_abb in higher_seed_probs
                    for lower_seed_abb in lower_seed_probs
                }
                prob_of_seed.update({seed_reward: dict()})
                for possible_matchup, prob_of_matchup in prob_of_matchups_dict.items():
                    higher_seed, lower_seed = possible_matchup[:3], possible_matchup[4:]
                    if seed_reward in current_state[this_round].keys():
                        current_state_of_matchup = current_state[this_round][
                            seed_reward
                        ]
                        higher_seed_won = current_state_of_matchup[higher_seed]
                        lower_seed_won = current_state_of_matchup[lower_seed]
                        if (higher_seed_won == 4) or (lower_seed_won == 4):
                            print(
                                f"{higher_seed}-{lower_seed} series was completed {higher_seed_won}-{lower_seed_won}"
                            )
                        else:
                            print(
                                f"{higher_seed}-{lower_seed} is currently in progress {higher_seed_won}-{lower_seed_won}"
                            )
                    else:
                        higher_seed_won, lower_seed_won = 0, 0
                    predict_series_dict = self.predict_series(
                        higher_seed,
                        lower_seed,
                        higher_already_won=higher_seed_won,
                        lower_already_won=lower_seed_won,
                        for_simulation=True,
                    )
                    if higher_seed not in predict_series_dict.keys():
                        prob_higher_seed_wins = 0
                    else:
                        prob_higher_seed_wins = np.sum(
                            list(predict_series_dict[higher_seed].values())
                        )
                    if higher_seed in prob_of_seed[seed_reward]:
                        prob_of_seed[seed_reward][higher_seed] += (
                            prob_higher_seed_wins * prob_of_matchup
                        )
                    else:
                        prob_of_seed[seed_reward].update(
                            {higher_seed: prob_higher_seed_wins * prob_of_matchup}
                        )
                    if lower_seed in prob_of_seed[seed_reward]:
                        prob_of_seed[seed_reward][lower_seed] += (
                            1 - prob_higher_seed_wins
                        ) * prob_of_matchup
                    else:
                        prob_of_seed[seed_reward].update(
                            {lower_seed: (1 - prob_higher_seed_wins) * prob_of_matchup}
                        )
            if this_round == "R4":
                round_probabilities = [
                    (team_abb, prob_of_seed[seed_reward][team_abb])
                    for team_abb in prob_of_seed[seed_reward]
                ]
                round_probabilities.sort(key=lambda x: x[1], reverse=True)
                print(f"_______NBA FINALS________")
                for team_prob in round_probabilities:
                    print(f"{team_prob[0]} wins: {round(team_prob[1] * 100, 2)}%")
                return
            winning_seeds_this_round = list(
                itertools.chain(*self.script[f"R{int(this_round[1]) + 1}"])
            )
            print(f"_______ROUND {this_round[1]}________")
            prob_of_round_dict = {}
            for team_abb in base_seeds.TEAM_ABB:
                total_prob = 0
                for winning_seed in winning_seeds_this_round:
                    try:
                        total_prob += prob_of_seed[winning_seed][team_abb]
                    except KeyError:
                        total_prob += 0
                prob_of_round_dict.update({team_abb: total_prob})
            round_probabilities = dict(
                sorted(prob_of_round_dict.items(), key=lambda item: -item[1])
            )
            for team_abb, prob in round_probabilities.items():
                print(f"{team_abb} wins: {round(prob * 100, 2)}%")
            print("\n \n \n")