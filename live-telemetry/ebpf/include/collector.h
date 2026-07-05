#ifndef __COLLECTOR_H
#define __COLLECTOR_H


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
};

#endif /* __COLLECTOR_H */