#include <stdio.h>
#include <stdlib.h>
#include <signal.h>
#include <unistd.h>


#include <bpf/libbpf.h>
#include <bpf/bpf.h>
#include "telemetry.h"
#include "../ebpf/include/collector.h"

#define BPF_OBJECT_PATH "../ebpf/build/collector.bpf.o"

//keep them global to clean up on exit
static struct bpf_object *obj = NULL; 
static struct ring_buffer *rb = NULL;

static struct bpf_link *insert_link = NULL;
static struct bpf_link *complete_link = NULL;

static struct bpf_program *insert_prog = NULL;
static struct bpf_program *complete_prog = NULL;

//prevent dangling attachments at Ctrl + C
static volatile sig_atomic_t exiting = 0;
static void handle_signal(int sig)
{
    exiting = 1;
}

static int handle_event(void *ctx, void *data, size_t data_sz)
{
    struct nestor_event *event = data;
    if (data_sz != sizeof(*event)) return 0;

    telemetry_process_event(event);

    return 0;
}

int main(void)
{
    signal(SIGINT, handle_signal);
    signal(SIGTERM, handle_signal);

    printf("Nestor loader starting...\n");

    obj = bpf_object__open_file(BPF_OBJECT_PATH, NULL); //open bpf file for verification/modification

    if (!obj) {
        fprintf(stderr, "Failed to open BPF object file\n");
        return EXIT_FAILURE;
    }


    int err;
    //.o->reads BTF->applies CO-RE relocations->runsverifier->loads programs
    err = bpf_object__load(obj); 

    if (err) {
        fprintf(stderr,
                "Failed to load BPF object: %d\n",
                err);

        bpf_object__close(obj);
        return EXIT_FAILURE;
    }

    printf("Successfully loaded BPF object.\n");

    insert_prog = bpf_object__find_program_by_name(obj,"handle_insert");

    if (!insert_prog) {
        fprintf(stderr, "Couldn't find handle_insert\n");
        bpf_object__close(obj);
        return EXIT_FAILURE;
    }

    complete_prog = bpf_object__find_program_by_name(obj,"handle_complete");

    if (!complete_prog) {
        fprintf(stderr, "Couldn't find handle_complete\n");
        bpf_object__close(obj);
        return EXIT_FAILURE;
    }


    insert_link = bpf_program__attach(insert_prog);
    
    if (libbpf_get_error(insert_link)) {
        fprintf(stderr, "Failed to attach insert probe\n");
        bpf_object__close(obj);
        return EXIT_FAILURE;
    }

    complete_link = bpf_program__attach(complete_prog);

    if (libbpf_get_error(complete_link)) {
        fprintf(stderr, "Failed to attach completion probe\n"); 
        bpf_link__destroy(insert_link);
        bpf_object__close(obj);
        return EXIT_FAILURE;
    }

    printf("Successfully attached both tracepoints.\n");

    struct bpf_map *events_map;
    int events_fd;

    events_map = bpf_object__find_map_by_name(obj, "events");

    if (!events_map) {
        fprintf(stderr, "Couldn't find events map\n");
        bpf_object__close(obj);
        return EXIT_FAILURE;
    }

    events_fd = bpf_map__fd(events_map);

    rb = ring_buffer__new(
    events_fd,
    handle_event,
    NULL,
    NULL    
    );

    if (!rb) {
    fprintf(stderr, "Failed to create ring buffer\n");
    bpf_object__close(obj);
    return EXIT_FAILURE;
    }

    telemetry_init();


    while (!exiting) {
        int err = ring_buffer__poll(rb, 100);

    if (err < 0) {
        fprintf(stderr, "Ring buffer polling failed: %d\n", err);
        break;
    }
    
    __u32 key = 0;
    __u64 dropped = 0;

    }
    
    telemetry_cleanup();

    printf("\nStopping collector...\n");

    ring_buffer__free(rb);

    bpf_link__destroy(insert_link);
    bpf_link__destroy(complete_link);

    bpf_object__close(obj);

    printf("Collector stopped.\n");

    return 0;
}