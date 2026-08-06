class StatsCreator:
    def __init__(self):
        self.total_tests = 0
        self.failed_tests = 0
        self.app_stats = {}

    def update(self, app_name, version, total, failed):
        # Update overall stats
        self.total_tests += total
        self.failed_tests += failed

        # Initialize app stats if not present
        if app_name not in self.app_stats:
            self.app_stats[app_name] = {}

        # Initialize version stats if not present
        if version not in self.app_stats[app_name]:
            self.app_stats[app_name][version] = {"total": 0, "failed": 0}

        # Update app and version stats
        self.app_stats[app_name][version]["total"] += total
        self.app_stats[app_name][version]["failed"] += failed

    def get_app_stats(self, app_name):
        return self.app_stats.get(app_name, {})

    def get_version_stats(self, app_name, version):
        return self.app_stats.get(app_name, {}).get(version, {"total": 0, "failed": 0})

    def __str__(self):
        overall_stats = f"Overall Testing: Total tests: {self.total_tests}, Failed tests: {self.failed_tests}\n"
        app_stats = "\n".join(
            f"{app}: {versions}" for app, versions in self.app_stats.items()
        )
        return overall_stats + app_stats
