"""
Maps predicted workload classes to the Linux I/O scheduler
best suited for that workload.

This is intentionally kept separate so the mapping can
be changed without retraining the ML model.
"""

SCHEDULER_MAP = {
    "seqread": {
        "scheduler": "mq-deadline",
        "reason": "Optimized for predictable sequential access."
    },

    "seqwrite": {
        "scheduler": "mq-deadline",
        "reason": "Maintains write ordering and minimizes latency."
    },

    "randread": {
        "scheduler": "none",
        "reason": "NVMe devices perform best without scheduler overhead."
    },

    "randwrite": {
        "scheduler": "none",
        "reason": "High IOPS random writes benefit from bypassing software scheduling."
    },

    "mixed_read": {
        "scheduler": "bfq",
        "reason": "Balances throughput and fairness for mixed workloads."
    },

    "mixed_write": {
        "scheduler": "kyber",
        "reason": "Controls latency effectively under write-heavy load."
    }
}


def recommend_scheduler(workload_class):
    """
    Returns the recommended scheduler for the predicted workload.
    """

    return SCHEDULER_MAP.get(workload_class, "none")