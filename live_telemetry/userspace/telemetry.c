#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <math.h>
#include <time.h>
#include <stdbool.h>
#include <sys/stat.h>
#include <errno.h>

#include "telemetry.h"

#define WINDOW_NS 1000000000ULL
#define JSON_PATH "/tmp/nestor/telemetry.jsonl"
#define MAX_DEVICES 16
#define MAX_LATENCY_SAMPLES 20000
#define BURST_HISTORY 30
#define MAX_WINDOW_REQUESTS 16384

static const char *csv_path = "/tmp/nestor/nestor_dataset.csv";
void telemetry_set_csv_path(const char *path)
{
    if (path && path[0] != '\0')
        csv_path = path;
}

static int compare_u32(const void *a, const void *b){
    __u32 x = *(__u32 *)a;
    __u32 y = *(__u32 *)b;

    if (x < y) return -1;
    if (x > y) return 1;
    return 0;
}

static FILE *json_file = NULL;
static FILE *csv_file = NULL;
static bool json_debug_enabled = false;
static char g_workload_class[64] = "unlabeled";


struct window_request {
    __u64 sector;
    __u32 bytes;
    __u8 op;
    __u64 issue_time_ns;
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

    /* Non-read/write ops (flush, discard, write-zeroes, etc).
     * Tracked separately, not mixed into read/write latency/percentiles,
     * since they're not comparable request types - but no longer
     * silently discarded either. */
    __u64 other_count;
    __u64 other_latency_sum_ns;

    __u32 iops_history[BURST_HISTORY];

    __u32 history_count;
    __u32 history_index;
    __u32 window_number;

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

    if (left->issue_time_ns < right->issue_time_ns) return -1;
    if (left->issue_time_ns > right->issue_time_ns) return 1;
    return 0;
}

/* How many prior requests (in issue order) to check for adjacency.
 * >1 lets us detect a sequential stream even when it's interleaved
 * with another concurrent stream in issue order (common at QD>1).
 * This is a heuristic, not true stream reconstruction - it can't
 * separate more concurrent streams than SEQ_LOOKBACK covers. */
#define SEQ_LOOKBACK 4

/* Below this many requests in a window, sequential-vs-random is too
 * noisy to be meaningful (e.g. count=2 can only ever be 0.0 or 1.0).
 * Caller should treat -1.0 as "not enough data", not "fully random". */
#define MIN_SEQ_SAMPLES 10

static double compute_sequential_ratio(struct window_request *requests, __u32 count)
{
    if (count < MIN_SEQ_SAMPLES)
        return -1.0;

    /* Sort by issue time (not sector!) so adjacency reflects the order
     * requests were actually issued, not just address-space density.
     * Completions can arrive out of issue order under concurrency, so
     * we can't rely on array order either - this recovers issue order
     * directly. */
    qsort(requests, count, sizeof(*requests), compare_window_requests);

    __u32 matches = 0;
    for (__u32 i = 1; i < count; ++i) {
        int is_sequential = 0;
        __u32 lookback = i < SEQ_LOOKBACK ? i : SEQ_LOOKBACK;

        for (__u32 j = 1; j <= lookback; ++j) {
            struct window_request *prev = &requests[i - j];
            struct window_request *cur  = &requests[i];

            __u64 tolerance = prev->bytes / 512;
            if (tolerance < 64)
                tolerance = 64;

            /* forward-sequential: cur starts where prev ended */
            __u64 fwd_expected = prev->sector + prev->bytes / 512;
            __u64 fwd_distance = cur->sector > fwd_expected ?
                cur->sector - fwd_expected : fwd_expected - cur->sector;

            /* backward-sequential: cur ends where prev started
             * (descending sequential access, e.g. some log-structured
             * writers) */
            __u64 cur_end = cur->sector + cur->bytes / 512;
            __u64 bwd_distance = cur_end > prev->sector ?
                cur_end - prev->sector : prev->sector - cur_end;

            if (fwd_distance <= tolerance || bwd_distance <= tolerance) {
                is_sequential = 1;
                break;
            }
        }

        if (is_sequential)
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
        for (__u32 i = 0; i < stats->history_count; i++)
            mean += stats->iops_history[i];

        mean /= stats->history_count;

        double variance = 0;
        for (__u32 i = 0; i < stats->history_count; i++) {
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

    //------------Other Ops (flush/discard/write-zeroes/unknown)----------
    snapshot.other_iops = stats->other_count;
    if (stats->other_count > 0) {
        snapshot.avg_other_latency_us =
            (double)stats->other_latency_sum_ns /
            stats->other_count /
            1000.0;
    }

    return snapshot;
}

//--------------------------------------------------------------------------------------------------------


static void print_features(struct telemetry_state *stats,
                           const struct telemetry_snapshot *snapshot) __attribute__((unused));
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
    printf("Other IOPS         : %llu\n", (unsigned long long)snapshot->other_iops);
    printf("Avg Other Latency  : %.2f us\n", snapshot->avg_other_latency_us);
    printf("===============================\n");
}

//--------------------------------------------------------------------------------------------------------


static void write_features_json(const struct telemetry_state *stats,
                                const struct telemetry_snapshot *snapshot,
                                __u64 window_start_ns)
{

    double timestamp = (double)window_start_ns / 1e9;

    /* Write one JSON object per line (NDJSON) so multiple windows append cleanly */
    fprintf(json_file,
        "{"
        "  \"disk_name\": \"%s\","
        "  \"timestamp\": %.3f,"
        "  \"read_iops\": %llu,"
        "  \"write_iops\": %llu,"
        "  \"read_throughput_mb\": %.3f,"
        "  \"write_throughput_mb\": %.3f,"
        "  \"avg_request_size\": %.3f,"
        "  \"avg_latency_us\": %.3f,"
        "  \"read_sequential_ratio\": %.3f,"
        "  \"write_sequential_ratio\": %.3f,"
        "  \"p50_latency_us\": %.3f,"
        "  \"p95_latency_us\": %.3f,"
        "  \"p99_latency_us\": %.3f,"
        "  \"avg_queue_depth\": %.3f,"
        "  \"read_write_ratio\": %.3f,"
        "  \"burstiness\": %.3f,"
        "  \"other_iops\": %llu,"
        "  \"avg_other_latency_us\": %.3f""}\n",
        stats->disk_name,
        timestamp,
        (unsigned long long)snapshot->read_iops,
        (unsigned long long)snapshot->write_iops,
        snapshot->read_throughput_mb,
        snapshot->write_throughput_mb,
        snapshot->avg_request_size,
        snapshot->avg_latency_us,
        snapshot->read_sequential_ratio,
        snapshot->write_sequential_ratio,
        snapshot->p50_latency_us,
        snapshot->p95_latency_us,
        snapshot->p99_latency_us,
        snapshot->avg_queue_depth,
        snapshot->read_write_ratio,
        snapshot->burstiness,
        (unsigned long long)snapshot->other_iops,
        snapshot->avg_other_latency_us);
    
    fflush(json_file);

}

static void write_csv_header(void)
{
    fprintf(csv_file,
        "workload_class,read_iops,write_iops,"
        "read_throughput_mb,write_throughput_mb,avg_request_size,"
        "avg_latency_us,read_sequential_ratio,write_sequential_ratio,"
        "p50_latency_us,p95_latency_us,p99_latency_us,avg_queue_depth,"
        "read_write_ratio,burstiness,other_iops,avg_other_latency_us\n");
    fflush(csv_file);
}

//--------------------------------------------------------------------------------------------------------

/* One CSV row per 1-second telemetry window - this is the training
 * dataset. Labeled with g_workload_class so windows collected under
 * a known fio workload can be used as ground truth. */
static void write_features_csv(const struct telemetry_state *stats,
                               const struct telemetry_snapshot *snapshot,
                               __u64 window_start_ns)
{
    (void)stats;
    (void)window_start_ns;

    if (!csv_file)
        return;

    fprintf(csv_file,
        "%s,%llu,%llu,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%llu,%.3f\n",
        g_workload_class,
        (unsigned long long)snapshot->read_iops,
        (unsigned long long)snapshot->write_iops,
        snapshot->read_throughput_mb,
        snapshot->write_throughput_mb,
        snapshot->avg_request_size,
        snapshot->avg_latency_us,
        snapshot->read_sequential_ratio,
        snapshot->write_sequential_ratio,
        snapshot->p50_latency_us,
        snapshot->p95_latency_us,
        snapshot->p99_latency_us,
        snapshot->avg_queue_depth,
        snapshot->read_write_ratio,
        snapshot->burstiness,
        (unsigned long long)snapshot->other_iops,
        snapshot->avg_other_latency_us);

    fflush(csv_file);
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

    stats->other_count = 0;
    stats->other_latency_sum_ns = 0;

    stats->latency_sample_count = 0;

    stats->queue_depth_sum = 0;
    stats->queue_depth_samples = 0;

    stats->read_request_count = 0;
    stats->write_request_count = 0;

}

    
void telemetry_init(const char *workload_class)
{
    if (mkdir("/tmp/nestor", 0755) == -1 && errno != EEXIST) {
        perror("mkdir");
    }
    printf("Telemetry initialized.\n");
    srand((unsigned int)time(NULL));

    if (workload_class && workload_class[0] != '\0') {
        strncpy(g_workload_class, workload_class, sizeof(g_workload_class) - 1);
        g_workload_class[sizeof(g_workload_class) - 1] = '\0';
    }

    /* CSV is always written, labeled or not - live commands (classify/
     * recommend/apply/monitor) never pass a workload_class and rely on
     * this file existing so collector.py can read features back. Dataset
     * generation writes to a separate path (nestor_dataset.csv) via
     * collect_dataset.sh, so there's no risk of unlabeled live-run rows
     * polluting the training set. */
    struct stat st;
    bool csv_has_content = (stat(csv_path, &st) == 0 && st.st_size > 0);

    csv_file = fopen(csv_path, "a");
    if (!csv_file) {
        fprintf(stderr, "Failed to open dataset file %s\n", csv_path);
    } else if (!csv_has_content) {
        write_csv_header();
    }

    /* JSON output is for debugging only now that CSV is the dataset
     * format - opt in with NESTOR_JSON_DEBUG=1 rather than always
     * paying the extra fopen/fprintf/fflush cost. */
    if (getenv("NESTOR_JSON_DEBUG")) {
        json_file = fopen(JSON_PATH, "a");
        if (!json_file) {
            fprintf(stderr, "Failed to open telemetry file %s\n", JSON_PATH);
        } else {
            json_debug_enabled = true;
            printf("JSON debug output enabled: %s\n", JSON_PATH);
        }
    }
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
        
        stats->window_number++;
        if (stats->window_number > 1) {
            struct telemetry_snapshot features = telemetry_features(stats);
            
            //print_features(stats, &features);
            write_features_csv(stats, &features, stats->window_start_ns - WINDOW_NS);

            if (json_debug_enabled)
                write_features_json(stats, &features, stats->window_start_ns - WINDOW_NS);
        }
        
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
            stats->read_requests[stats->read_request_count].issue_time_ns =
                event->completion_time_ns - event->latency_ns;
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
            stats->write_requests[stats->write_request_count].issue_time_ns =
                event->completion_time_ns - event->latency_ns;
            stats->write_request_count++;
        }
    }
    else {
        /* flush/discard/write-zeroes/unknown ops. Still real device
         * activity (and already counted toward queue depth above) -
         * track presence + latency separately instead of vanishing
         * entirely. Kept out of read/write percentiles since mixing
         * a flush's latency in with read/write latency would skew
         * those distributions. */
        stats->other_count++;
        stats->other_latency_sum_ns += event->latency_ns;
        return;
    }

    stats->request_count++;
    stats->latency_sum_ns += event->latency_ns;

    /* Reservoir sampling (Algorithm R): once the reservoir is full,
     * each new sample has a MAX_LATENCY_SAMPLES/n chance of replacing
     * a random existing entry. This keeps the sample an unbiased
     * cross-section of the whole window, instead of always being
     * just the first MAX_LATENCY_SAMPLES requests (which biased
     * percentiles toward the start of the window on high-IOPS
     * devices that exceed the cap). stats->request_count is the
     * 1-indexed count of samples seen so far in this window. */
    if (stats->latency_sample_count < MAX_LATENCY_SAMPLES) {
        stats->latency_samples[stats->latency_sample_count++] =
            event->latency_ns / 1000;
    } else {
        __u64 j = rand() % stats->request_count;
        if (j < MAX_LATENCY_SAMPLES)
            stats->latency_samples[j] = event->latency_ns / 1000;
    }

}

void telemetry_cleanup(void)
{
    printf("Telemetry stopped.\n");

    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts) == 0) {
        __u64 now_ns = (__u64)ts.tv_sec * 1000000000ULL + (__u64)ts.tv_nsec;

        for (int i = 0; i < num_devices; ++i) {
            struct telemetry_state *stats = &devices[i];
            if (stats->disk_name[0] == '\0' || stats->request_count == 0)
                continue;

            if (stats->window_start_ns != 0 && now_ns - stats->window_start_ns >= WINDOW_NS) {
                stats->window_number++;
                if (stats->window_number > 1) {
                    struct telemetry_snapshot features = telemetry_features(stats);
                    write_features_csv(stats, &features, stats->window_start_ns);
                    if (json_debug_enabled)
                        write_features_json(stats, &features, stats->window_start_ns);
                }
            }
        }
    }

    if (csv_file) {
        fclose(csv_file);
        csv_file = NULL;
    }

    if (json_file) {
        fclose(json_file);
        json_file = NULL;
    }
}