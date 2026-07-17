#!/usr/bin/env python3

"""
Pretty terminal output for Nestor.
"""

from .utils import separator


def banner():

    separator()

    print(
r"""
 _   _           _             
| \ | | ___  ___| |_ ___  _ __ 
|  \| |/ _ \/ __| __/ _ \| '__|
| |\  |  __/\__ \ || (_) | |   
|_| \_|\___||___/\__\___/|_|   

Linux Storage Workload Advisor
"""
    )

    separator()
    print()


def workload(result):

    separator()

    print("Detected Workload")

    separator("-")

    print(f"\nWorkload   : {result['workload']}")
    print(f"Confidence : {result['confidence']*100:.2f}%")

    print("\nClass Probabilities\n")

    probs = sorted(
        result["probabilities"].items(),
        key=lambda x: x[1],
        reverse=True,
    )

    for workload, probability in probs:

        print(
            f"{workload:<22}"
            f"{probability*100:6.2f}%"
        )

    print()


def recommendation(result, recommendations):

    separator()

    print("Scheduler Recommendation")

    separator("-")

    print(
        f"\nDetected workload : {result['workload']}"
    )

    print(
        f"Confidence        : "
        f"{result['confidence']*100:.2f}%"
    )

    print("\nRecommended Schedulers\n")

    for i, rec in enumerate(recommendations, start=1):

        print(f"{i}. {rec['scheduler']}")
        print(f"   Confidence : {rec['confidence']}")
        print(f"   Reason     : {rec['reason']}\n")


def applied(scheduler):

    separator()

    print("Scheduler Applied")

    separator("-")

    print(f"\nCurrent scheduler: {scheduler}\n")


def monitoring(result):

    separator()

    print(
        f"Workload   : {result['workload']}"
    )

    print(
        f"Confidence : "
        f"{result['confidence']*100:.2f}%"
    )

    separator()