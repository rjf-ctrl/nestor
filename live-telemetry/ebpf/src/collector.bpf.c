#include "../include/vmlinux.h"

#include <bpf/bpf_helpers.h>
#include <bpf/bpf_core_read.h>
#include <bpf/bpf_tracing.h>

#include "../include/collector.h"

/*
 * Block operation encoding.
 * Verified against: Linux 6.19
 * include/linux/blk_types.h
 */


#define REQ_OP_BITS   8
#define REQ_OP_MASK   ((1U << REQ_OP_BITS) - 1)
#define REQ_OP_READ   0
#define REQ_OP_WRITE  1

//temporary struct to hold request information.
struct request_info {
    __u64 insert_time_ns;

    __u64 sector;
    __u32 bytes;

    __u8 op;
    __u32 queue_depth;
    char disk_name[32];
};
//--------------------------------------------------------------------------------------------------------
//getting the io operation from the cmd_flags
static __always_inline __u8 get_io_operation(struct request *rq)
{
    __u32 cmd_flags = BPF_CORE_READ(rq, cmd_flags);

    __u32 op = cmd_flags & REQ_OP_MASK;
    
    switch (op) {

    case REQ_OP_READ:
        return IO_READ;

    case REQ_OP_WRITE:
        return IO_WRITE;

    default:
        return IO_UNKNOWN;
    }
    
    return op;
    
}

//--------------------------------------------------------------------------------------------------------
//ensures that every request_info is fully initialised in one place
static __always_inline void fill_request_info(struct request *rq,     //always_inline so that compiler directly copies code into kprobe rather than create a function call
                                              struct request_info *info)  //veriier likes small predicatable code and also avoid function call overhead
{
    //time when reuquest enters scheduler
    info->insert_time_ns = bpf_ktime_get_ns();  

    // instead of info->sector = rq->sector as CORE performs a relocation so field offsets can change across kernel versions
    info->sector = BPF_CORE_READ(rq, __sector); 

    //also CO-RE safe
    info->bytes = BPF_CORE_READ(rq, __data_len);
    
    
    info->op = get_io_operation(rq);

    const char *name = BPF_CORE_READ(rq, q, disk, disk_name);

    bpf_core_read_str(info->disk_name, sizeof(info->disk_name), name);
}

//compares two disk_name buffers (max 32 bytes, NUL-terminated)
static __always_inline int disk_name_eq(const char *a, const char *b)
{
    for (int i = 0; i < 32; i++) {
        if (a[i] != b[i])
            return 0;
        if (a[i] == '\0')
            break;
    }
    return 1;
}

//------------------------------MAPS----------------------------------------------------------------------
//request tracking map. Key is request pointer, value is request_info
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 16384);  
    //only need enough entries to hold currently outstanding requests
    //even busy NVMe drives will not have more than a few thousand active requests at a time.

    __type(key, struct request *);
    __type(value, struct request_info);

} request_map SEC(".maps"); 


//ring buffer to send nestor_event to userspace
struct {
    __uint(type, BPF_MAP_TYPE_RINGBUF);
    __uint(max_entries, 1 << 20);   // 1 MB ring buffer
} events SEC(".maps");

struct device_queue_depth {
    struct bpf_spin_lock lock;
    __u32 depth;
};

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 64);

    __type(key, char[32]);
    __type(value, struct device_queue_depth);

} queue_depth_map SEC(".maps");

//single-entry config map: set by loader.c to optionally restrict
//collection to one target device
struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, 1);

    __type(key, __u32);
    __type(value, struct collector_config);

} config_map SEC(".maps");

//--------------------------BPF PROGRAMS--------------------------------------------------------------------------

//issue request
SEC("tp_btf/block_rq_issue")
int BPF_PROG(handle_insert, struct request *rq){  //Because our probe runs at the function entry, we receive the same pointer.(rq)

    struct request_info info = {}; //zero-intialisation to avoid verifier complaints abt uninitialised memory
    fill_request_info(rq, &info);

    __u32 cfg_key = 0;
    struct collector_config *cfg = bpf_map_lookup_elem(&config_map, &cfg_key);
    if (cfg && cfg->filter_enabled && !disk_name_eq(info.disk_name, cfg->disk_name))
        return 0; //not the target device, skip tracking entirely

    struct device_queue_depth *qd;

    qd = bpf_map_lookup_elem(&queue_depth_map, info.disk_name);

    if (qd) {
        bpf_spin_lock(&qd->lock);
        qd->depth++;
        info.queue_depth = qd->depth;
        bpf_spin_unlock(&qd->lock);
    } else {
        struct device_queue_depth init = {
            .depth = 1,
        };

        bpf_map_update_elem(
            &queue_depth_map,
            info.disk_name,
            &init,
            BPF_ANY);

        info.queue_depth = 1;
    }

    bpf_map_update_elem(&request_map, &rq, &info, BPF_ANY);
    
    return 0; //let kernel continue processing the request, we just want to track it

}

//--------------------------------------------------------------------------------------------------------
//complete request
SEC("tp_btf/block_rq_complete")
int BPF_PROG(handle_complete, struct request *rq){

    struct request_info *info = bpf_map_lookup_elem(&request_map, &rq);
    if(!info) return 0;

    __u64 completion_time_ns = bpf_ktime_get_ns();
    __u64 latency_ns = completion_time_ns - info->insert_time_ns;

    
    struct nestor_event *event;
    event = bpf_ringbuf_reserve(&events, sizeof(*event), 0);

    if (!event) {

        struct device_queue_depth *qd =
            bpf_map_lookup_elem(&queue_depth_map,
                                info->disk_name);

        if (qd) {
            bpf_spin_lock(&qd->lock);
            if (qd->depth > 1)
                qd->depth--;
            else
                qd->depth = 0;
            bpf_spin_unlock(&qd->lock);
        }

        bpf_map_delete_elem(&request_map, &rq);
        return 0;
    }
   

    event->completion_time_ns = completion_time_ns;
    event->latency_ns         = latency_ns;
    event->sector             = info->sector;
    event->bytes              = info->bytes;
    event->op                 = info->op;
    __builtin_memcpy(event->disk_name, info->disk_name,sizeof(info->disk_name));
    struct device_queue_depth *qd;
    event->queue_depth = info->queue_depth;

    qd = bpf_map_lookup_elem(&queue_depth_map,info->disk_name);
    if (qd) {
        bpf_spin_lock(&qd->lock);
        if (qd->depth > 1)
            qd->depth--;
        else
            qd->depth = 0;
        bpf_spin_unlock(&qd->lock);
    }
    

    bpf_ringbuf_submit(event, 0);


    

    bpf_map_delete_elem(&request_map, &rq);
    return 0;    
}

//--------------------------------------------------------------------------------------------------------

char LICENSE[] SEC("license") = "GPL";