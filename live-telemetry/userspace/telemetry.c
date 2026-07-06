#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <math.h>

#include "telemetry.h"

#define WINDOW_NS 1000000000ULL
#define MAX_DEVICES 16
#define MAX_LATENCY_SAMPLES 20000
#define BURST_HISTORY 30
#define MAX_WINDOW_REQUESTS 16384

static int compare_u32(const void *a, const void *b){
    __u32 x = *(__u32 *)a;
    __u32 y = *(__u32 *)b;

    if (x < y) return -1;
    if (x > y) return 1;
    return 0;
}

struct window_request {
    __u64 sector;
    __u32 bytes;
    __u8 op;
};

struct telemetry_state {
    char disk_name[32];

    __u64 window_start_ns;

    __u64 read_count;
    __u64 write_count;

    __u64 read_bytes;
    __u64 write_bytes;

    __u64 latency_sum_ns;
    __u32 latency_samples[MAX_LATENCY_SAMPLES];
    __u32 latency_sample_count;

    __u64 request_count;

    __u32 iops_history[BURST_HISTORY];

    __u32 history_count;
    __u32 history_index;

    __u64 queue_depth_sum;
    __u64 queue_depth_samples;

    struct window_request read_requests[MAX_WINDOW_REQUESTS];
    struct window_request write_requests[MAX_WINDOW_REQUESTS];
    __u32 read_request_count;
    __u32 write_request_count;
};

static struct telemetry_state devices[MAX_DEVICES];
static int num_devices = 0;

static int compare_window_requests(const void *a, const void *b)
{
    const struct window_request *left = (const struct window_request *)a;
    const struct window_request *right = (const struct window_request *)b;

    if (left->sector < right->sector) return -1;
    if (left->sector > right->sector) return 1;
    return 0;
}

static double compute_sequential_ratio(struct window_request *requests, __u32 count)
{
    if (count <= 1)
        return 0.0;

    qsort(requests, count, sizeof(*requests), compare_window_requests);

    __u32 matches = 0;
    for (__u32 i = 1; i < count; ++i) {
        __u64 expected = requests[i - 1].sector + requests[i - 1].bytes / 512;
        __u64 distance = requests[i].sector > expected ?
            requests[i].sector - expected : expected - requests[i].sector;

        __u64 tolerance = requests[i - 1].bytes / 512;
        if (tolerance < 64)
            tolerance = 64;

        if (distance <= tolerance)
            matches++;
    }

    return (double)matches / (double)(count - 1);
}

//--------------------------------------------------------------------------------------------------------
static struct telemetry_state *find_device(const char *name){
    
    /* Look for an existing device */
    for (int i = 0; i <num_devices; i++) {

        if (devices[i].disk_name[0] == '\0')
            continue;

        if (strcmp(devices[i].disk_name, name) == 0)
            return &devices[i];
    }

    if (num_devices >= MAX_DEVICES)
        return NULL;

    /* Allocate a new slot */
    for (int i = 0; i < MAX_DEVICES; i++) {
        if (devices[i].disk_name[0] == '\0') {
            devices[i] = (struct telemetry_state){0};
            
            size_t len = sizeof(devices[i].disk_name);
            strncpy(devices[i].disk_name, name, len - 1);
            devices[i].disk_name[len - 1] = '\0';

            num_devices++;
            return &devices[i];
        }
    }

    /* No free slot */
    return NULL;
}

//--------------------------------------------------------------------------------------------------------


struct telemetry_snapshot telemetry_features(struct telemetry_state *stats)
{
    struct telemetry_snapshot snapshot = {0};

    //------------IOPS---------------------------------- 
    snapshot.read_iops = stats->read_count;
    snapshot.write_iops = stats->write_count;

    //------------Throughput (MB/s)----------------------
    snapshot.read_throughput_mb =
        (double)stats->read_bytes / (1024.0 * 1024.0);

    snapshot.write_throughput_mb =
        (double)stats->write_bytes / (1024.0 * 1024.0);

    //------------Average Request Size (bytes)----------------------
    if (stats->request_count > 0) {
        snapshot.avg_request_size =
            (double)(stats->read_bytes + stats->write_bytes) /
            stats->request_count;
    }

    //------------Sequential Ratios----------------------
    snapshot.read_sequential_ratio = compute_sequential_ratio(
        stats->read_requests,
        stats->read_request_count);

    snapshot.write_sequential_ratio = compute_sequential_ratio(
        stats->write_requests,
        stats->write_request_count);

    //------------Read/Write Ratio----------------------
    if (stats->write_count > 0) {
        snapshot.read_write_ratio =
            (double)stats->read_count / stats->write_count;
    } else if (stats->read_count > 0) {
        snapshot.read_write_ratio = -1.0;
    }

    //------------Average Latency (microseconds)----------------------
    if (stats->request_count > 0) {
        snapshot.avg_latency_us =
            (double)stats->latency_sum_ns /
            stats->request_count /
            1000.0;
    }

    //------------Percentile Latencies (microseconds)----------------------
    if (stats->latency_sample_count > 0){
        __u32 temp[MAX_LATENCY_SAMPLES];

        memcpy(temp,
            stats->latency_samples,
            stats->latency_sample_count * sizeof(__u32));

        qsort(temp,
            stats->latency_sample_count,
            sizeof(__u32),
            compare_u32);

        int n = stats->latency_sample_count;

        snapshot.p50_latency_us =
            temp[(int)(0.50 * (n - 1))];

        snapshot.p95_latency_us =
            temp[(int)(0.95 * (n - 1))];

        snapshot.p99_latency_us =
            temp[(int)(0.99 * (n - 1))];
    }
    

    //------------Burst Detection----------------------
    if (stats->history_count > 1) {

        double mean = 0;
        for (int i = 0; i < stats->history_count; i++)
            mean += stats->iops_history[i];

        mean /= stats->history_count;

        double variance = 0;
        for (int i = 0; i < stats->history_count; i++) {
            double d = stats->iops_history[i] - mean;
            variance += d * d;
        }

        variance /= (stats->history_count-1);

        double stddev = sqrt(variance);
        if (mean > 0)
            snapshot.burstiness = stddev / mean;
    }

    //------------Average Queue Depth----------------------
    if (stats->queue_depth_samples > 0) {
        snapshot.avg_queue_depth =  (double)stats->queue_depth_sum /stats->queue_depth_samples;
    }

    return snapshot;
}

//--------------------------------------------------------------------------------------------------------


static void print_features(struct telemetry_state *stats,
                           const struct telemetry_snapshot *snapshot)
{
    printf("\n========== %s ==========\n", stats->disk_name);
    printf("Read IOPS          : %llu\n", snapshot->read_iops);
    printf("Write IOPS         : %llu\n", snapshot->write_iops);
    printf("Read Throughput    : %.2f MB/s\n", snapshot->read_throughput_mb);
    printf("Write Throughput   : %.2f MB/s\n", snapshot->write_throughput_mb);
    printf("Avg Request Size   : %.2f bytes\n", snapshot->avg_request_size);
    printf("Avg Latency        : %.2f us\n", snapshot->avg_latency_us);
    printf("Read Sequential Ratio   : %.2f\n", snapshot->read_sequential_ratio);
    printf("Write Sequential Ratio   : %.2f\n", snapshot->write_sequential_ratio);
    printf("P50 Latency        : %.2f us\n", snapshot->p50_latency_us);
    printf("P95 Latency        : %.2f us\n", snapshot->p95_latency_us);
    printf("P99 Latency        : %.2f us\n", snapshot->p99_latency_us);
    printf("Avg Queue Depth    : %.2f\n", snapshot->avg_queue_depth);
    printf("Read/Write Ratio   : %.2f\n",snapshot->read_write_ratio);
    printf("Burstiness         : %.2f\n", snapshot->burstiness);
    printf("===============================\n");
}

//--------------------------------------------------------------------------------------------------------


static void reset_window(struct telemetry_state *stats)
{
    /* keep window_start_ns as-is (caller advances it) */
    stats->read_count = 0;
    stats->write_count = 0;

    stats->read_bytes = 0;
    stats->write_bytes = 0;

    stats->latency_sum_ns = 0;
    stats->request_count = 0;

    stats->latency_sample_count = 0;

    stats->queue_depth_sum = 0;
    stats->queue_depth_samples = 0;

    stats->read_request_count = 0;
    stats->write_request_count = 0;

}

void telemetry_init(void)
{
    printf("Telemetry initialized.\n");
}

//--------------------------------------------------------------------------------------------------------

void telemetry_process_event(const struct nestor_event *event)
{
    struct telemetry_state *stats = find_device(event->disk_name);
    if (!stats) {
        fprintf(stderr, "No free telemetry slot for device %s\n", event->disk_name);
        return;
    }

    if (stats->window_start_ns == 0)
        stats->window_start_ns = event->completion_time_ns;

    /* Has the current window ended? */
    if (event->completion_time_ns - stats->window_start_ns >= WINDOW_NS) {

        while (event->completion_time_ns - stats->window_start_ns >= WINDOW_NS)
            stats->window_start_ns += WINDOW_NS;

        //burst detection: store the current IOPS in the history buffer
        __u32 current_iops = stats->read_count + stats->write_count;

        stats->iops_history[stats->history_index] = current_iops;
        stats->history_index = (stats->history_index + 1) % BURST_HISTORY;
        if (stats->history_count < BURST_HISTORY)
            stats->history_count++;
        
        struct telemetry_snapshot features = telemetry_features(stats);
        
        print_features(stats, &features);
        
        reset_window(stats);
    }

    stats->queue_depth_sum += event->queue_depth;
    stats->queue_depth_samples++;


    /* Account for the current event in the (new) window */
    if (event->op == IO_READ) {
        stats->read_count++;
        stats->read_bytes += event->bytes;

        if (stats->read_request_count < MAX_WINDOW_REQUESTS) {
            stats->read_requests[stats->read_request_count].sector = event->sector;
            stats->read_requests[stats->read_request_count].bytes = event->bytes;
            stats->read_requests[stats->read_request_count].op = event->op;
            stats->read_request_count++;
        }
    }
    else if (event->op == IO_WRITE) {
        stats->write_count++;
        stats->write_bytes += event->bytes;

        if (stats->write_request_count < MAX_WINDOW_REQUESTS) {
            stats->write_requests[stats->write_request_count].sector = event->sector;
            stats->write_requests[stats->write_request_count].bytes = event->bytes;
            stats->write_requests[stats->write_request_count].op = event->op;
            stats->write_request_count++;
        }
    }
    else {
        return;
    }

    stats->request_count++;
    stats->latency_sum_ns += event->latency_ns;
    if (stats->latency_sample_count < MAX_LATENCY_SAMPLES){
        stats->latency_samples[stats->latency_sample_count++] =
            event->latency_ns / 1000;
    }

}

void telemetry_cleanup(void)
{
    printf("Telemetry stopped.\n");
}