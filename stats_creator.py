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
        rows = []
        for app_name, versions in self.app_stats.items():
            for version, values in versions.items():
                rows.append(
                    (
                        app_name,
                        version,
                        str(values["total"]),
                        str(values["failed"]),
                    )
                )

        headers = ("Application", "Version", "Total", "Failed")
        rows.append(
            (
                "Overall",
                "-",
                str(self.total_tests),
                str(self.failed_tests),
            )
        )

        widths = [
            max(len(header), *(len(row[index]) for row in rows))
            for index, header in enumerate(headers)
        ]

        def format_row(row):
            return "| " + " | ".join(
                value.ljust(width)
                for value, width in zip(row, widths)
            ) + " |"

        separator = "+" + "+".join("-" * (width + 2) for width in widths) + "+"

        return "\n".join(
            [
                "Resolver test summary",
                separator,
                format_row(headers),
                separator,
                *(format_row(row) for row in rows),
                separator,
            ]
        )
