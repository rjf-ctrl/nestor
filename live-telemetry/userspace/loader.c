#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
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

int main(int argc, char **argv)
{
    signal(SIGINT, handle_signal);
    signal(SIGTERM, handle_signal);

    bool filtering = argc > 1;

    printf("Nestor loader starting...\n");

    if (filtering) {
        printf("Filtering collection to device: %s\n", argv[1]);
    } else {
        printf("No device filter set, collecting from all devices.\n");
    }

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

    /* Config map must be written before probes are attached, so no
     * request can slip through with an empty/default config. */
    if (filtering) {
        struct bpf_map *config_map = bpf_object__find_map_by_name(obj, "config_map");

        if (!config_map) {
            fprintf(stderr, "Couldn't find config_map\n");
            bpf_object__close(obj);
            return EXIT_FAILURE;
        }

        struct collector_config cfg = { .filter_enabled = 1 };
        strncpy(cfg.disk_name, argv[1], sizeof(cfg.disk_name) - 1);
        cfg.disk_name[sizeof(cfg.disk_name) - 1] = '\0';

        __u32 cfg_key = 0;
        int cfg_fd = bpf_map__fd(config_map);

        if (bpf_map_update_elem(cfg_fd, &cfg_key, &cfg, BPF_ANY)) {
            fprintf(stderr, "Failed to set device filter\n");
            bpf_object__close(obj);
            return EXIT_FAILURE;
        }
    }

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