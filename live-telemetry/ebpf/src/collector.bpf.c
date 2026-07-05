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
};

//getting the io operation from the cmd_flags
static __always_inline __u8 get_io_operation(struct request *rq)
{
    __u32 cmd_flags = BPF_CORE_READ(rq, cmd_flags);

    __u32 op = cmd_flags & REQ_OP_MASK;
    /*
    switch (op) {

    case REQ_OP_READ:
        return IO_READ;

    case REQ_OP_WRITE:
        return IO_WRITE;

    default:
        return IO_UNKNOWN;
    }
    */
    return op;
    
}

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
}


//request tracking map. Key is request pointer, value is request_info
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 16384);  
    //only need enough entries to hold currently outstanding requests
    //even busy NVMe drives will not have more than a few thousand active requests at a time.

    __type(key, struct request *);
    __type(value, struct request_info);

} request_map SEC(".maps"); 



SEC("tp_btf/block_rq_issue")
int BPF_PROG(handle_insert, struct request *rq){  //Because our probe runs at the function entry, we receive the same pointer.(rq)

    struct request_info info = {}; //zero-intialisation to avoid verifier complaints abt uninitialised memory
    fill_request_info(rq, &info);
    bpf_map_update_elem(&request_map, &rq, &info, BPF_ANY);
    bpf_printk(
    "kernel_op=%u sector=%llu bytes=%u",
    info.op,
    info.sector,
    info.bytes
    );
    return 0; //let kernel continue processing the request, we just want to track it

}




SEC("tp_btf/block_rq_complete")
int BPF_PROG(handle_complete, struct request *rq){

    struct request_info *info = bpf_map_lookup_elem(&request_map, &rq);
    if(!info) return 0;

    __u64 completion_time_ns = bpf_ktime_get_ns();
    __u64 latency_ns = completion_time_ns - info->insert_time_ns;

    struct nestor_event event = {
        .completion_time_ns = completion_time_ns,
        .latency_ns = latency_ns,
        .sector = info->sector,
        .bytes = info->bytes,
        .op = info->op
    };

    bpf_printk(
        "COMPLETE sector=%llu bytes=%u latency=%llu ns",
        event.sector,
        event.bytes,
        event.latency_ns
    );

    bpf_map_delete_elem(&request_map, &rq);
    return 0;    
}
               

char LICENSE[] SEC("license") = "GPL";