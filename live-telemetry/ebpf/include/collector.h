#ifndef __COLLECTOR_H
#define __COLLECTOR_H

#ifndef __BPF__
#include <linux/types.h>
#endif

/*
 * Operation type.
 * These values are sent to userspace.
 */
enum io_op {
    IO_UNKNOWN = 0,
    IO_READ    = 1,
    IO_WRITE   = 2,
};

/*
 * Event emitted after an I/O request completes.
 * This is the interface between kernel-space and userspace.
 */


struct nestor_event {
    __u64 completion_time_ns;
    __u64 latency_ns;
    __u64 sector;
    __u32 bytes;
    __u8 op;
    __u32 queue_depth;
    char disk_name[32];
};

/*
 * Optional collection-time filter.
 * When filter_enabled is 0, every device is tracked (use this for
 * realistic/noisy validation runs). When set to 1, only disk_name
 * is tracked (use this for clean single-workload training collection).
 */
struct collector_config {
    char disk_name[32];
    __u8 filter_enabled;
};

#endif /* __COLLECTOR_H */