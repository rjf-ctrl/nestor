#ifndef TELEMETRY_H
#define TELEMETRY_H

#include "../ebpf/include/collector.h"

/* workload_class: label attached to every CSV row this run produces
 * (e.g. "seq_read", "rand_write_qd16"). Pass NULL for unlabeled/general
 * collection runs. */
void telemetry_init(const char *workload_class);
void telemetry_process_event(const struct nestor_event *event);
void telemetry_cleanup(void);

struct telemetry_snapshot {
    __u64 read_iops;
    __u64 write_iops;

    double read_throughput_mb;
    double write_throughput_mb;

    double avg_request_size;
    double avg_latency_us;


    double p50_latency_us;
    double p95_latency_us;
    double p99_latency_us;

  
    double read_sequential_ratio;
    double write_sequential_ratio;

    double read_write_ratio;
    double avg_queue_depth;
    double burstiness;

    /* flush/discard/write-zeroes/unknown ops - tracked, not discarded */
    __u64 other_iops;
    double avg_other_latency_us;
};


#endif