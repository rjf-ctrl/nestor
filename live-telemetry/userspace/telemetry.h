#ifndef TELEMETRY_H
#define TELEMETRY_H

#include "../ebpf/include/collector.h"

void telemetry_init(void);
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
};


#endif