import json
from pathlib import Path

class SchedulerAdvisor:

    def __init__(self, json_file=None):

        if json_file is None:
            json_file = (
                Path(__file__).resolve().parent
                / "scheduler_heuristics.json"
            )

        with open(json_file, "r") as f:
            self.heuristics = json.load(f)

    def recommend(self, workload_class):

        recommendations = self.heuristics.get(workload_class)

        if recommendations is None:
            raise ValueError(
                f"No heuristic available for '{workload_class}'."
            )
        """
        print("=" * 60)
        print(f"Detected workload : {workload_class}")
        print("=" * 60)

        print("\nRecommended schedulers:\n")

        for i, rec in enumerate(recommendations, start=1):

            print(f"{i}. {rec['scheduler']}")
            print(f"   Confidence : {rec['confidence']}")
            print(f"   Reason     : {rec['reason']}\n")
        """
        return recommendations


if __name__ == "__main__":

    advisor = SchedulerAdvisor()

    advisor.recommend("randwrite")