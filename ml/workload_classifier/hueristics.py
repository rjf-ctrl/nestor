import json


class SchedulerAdvisor:

    def __init__(self, json_file="scheduler_heuristics.json"):
        with open(json_file, "r") as f:
            self.heuristics = json.load(f)

    def recommend(self, workload_class):

        recommendations = self.heuristics.get(workload_class)

        if recommendations is None:
            print(f"No heuristic available for '{workload_class}'.")
            return

        print("=" * 60)
        print(f"Detected workload : {workload_class}")
        print("=" * 60)

        print("\nRecommended schedulers:\n")

        for i, rec in enumerate(recommendations, start=1):

            print(f"{i}. {rec['scheduler']}")
            print(f"   Confidence : {rec['confidence']}")
            print(f"   Reason     : {rec['reason']}\n")


if __name__ == "__main__":

    advisor = SchedulerAdvisor()

    advisor.recommend("randwrite")