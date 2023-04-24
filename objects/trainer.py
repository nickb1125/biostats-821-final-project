"""Trainer class."""

class training_dataset:
    def __init__(self, since=2000):
        self.training_sets_cache = dict()
        self.years_cache = dict()
        self.since = since
        print(
            f"Loading NBA data from {self.since} until {datetime.datetime.now().year - 2}..."
        )
        self.load_year_data()

    def get_training_dataset(
        self, injury_adjusted: bool, avg_minutes_played_cutoff: int, force_update: bool
    ):
        settings_string = f"injury_adjusted = {injury_adjusted}, avg_minutes_played_cutoff = {avg_minutes_played_cutoff}"
        if (force_update == True) or (
            self.since not in self.training_sets_cache.keys()
        ):
            self.load_train_data(
                injury_adjusted=injury_adjusted,
                avg_minutes_played_cutoff=avg_minutes_played_cutoff,
            )
        elif settings_string not in self.training_sets_cache.get(self.since).keys():
            self.load_train_data(
                injury_adjusted=injury_adjusted,
                avg_minutes_played_cutoff=avg_minutes_played_cutoff,
            )
        all_train = []
        for year, settings_dict in self.training_sets_cache.items():
            all_train.append(settings_dict.get(settings_string))
        return pd.concat(all_train)

    def year(self, year_id):
        """Get year object."""
        return self.years_cache.get(year_id)

    def load_year_data(self):
        """Load all year classes."""
        for year_get in range(self.since, datetime.datetime.now().year - 2):
            try:
                self.years_cache.update({year_get: year(year_get)})
            except:
                print("Timeout occured. Try one more time.")
                time.sleep(60)
                self.years_cache.update({year_get: year(year_get)})

    def load_train_data(
        self, injury_adjusted: bool, avg_minutes_played_cutoff: int
    ) -> None:
        """Load training and outcomes for all years."""
        print(
            f"Loading training data for years from from {self.since} until {datetime.datetime.now().year - 2}..."
        )
        for year_load in range(self.since, datetime.datetime.now().year - 2):
            print(
                f"---->Loading training for {year_load} with injury_adjustments = {injury_adjusted} and avg_minutes_played_cutoff = {avg_minutes_played_cutoff}..."
            )
            training = self.year(year_load).get_train_for_all_playoff_games(
                injury_adjusted=injury_adjusted,
                avg_minutes_played_cutoff=avg_minutes_played_cutoff,
            )
            if year_load not in self.training_sets_cache.keys():
                self.training_sets_cache.update(
                    {
                        year_load: {
                            f"injury_adjusted = {injury_adjusted}, avg_minutes_played_cutoff = {avg_minutes_played_cutoff}": training
                        }
                    }
                )
            else:
                self.training_sets_cache.get(year_load).update(
                    {
                        f"injury_adjusted = {injury_adjusted}, avg_minutes_played_cutoff = {avg_minutes_played_cutoff}": training
                    }
                )