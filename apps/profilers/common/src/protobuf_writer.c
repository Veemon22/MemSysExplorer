/*
 * Protobuf Writer Implementation
 */

#include "protobuf_writer.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

#ifdef HAVE_PROTOBUF_C

/* Memory Trace Writer Structure */
struct pb_trace_writer {
    FILE *file;
    MemoryTrace__MemoryTrace *trace;
    size_t event_capacity;
    size_t event_count;
};

/* Time-Series Writer Structure */
struct pb_timeseries_writer {
    FILE *file;
    Memsys__Timeseries__TimeSeriesData *data;
    size_t sample_capacity;
    size_t sample_count;
};

/* ========== Memory Trace Writer ========== */

pb_trace_writer_t* pb_trace_writer_create(const char *filename) {
    pb_trace_writer_t *writer = (pb_trace_writer_t*)malloc(sizeof(pb_trace_writer_t));
    if (!writer) return NULL;

    writer->file = fopen(filename, "wb");
    if (!writer->file) {
        free(writer);
        return NULL;
    }

    /* Initialize protobuf message */
    writer->trace = (MemoryTrace__MemoryTrace*)malloc(sizeof(MemoryTrace__MemoryTrace));
    memory_trace__memory_trace__init(writer->trace);

    /* Pre-allocate event array */
    writer->event_capacity = 1024;
    writer->event_count = 0;
    writer->trace->events = (MemoryTrace__MemoryEvent**)
        malloc(writer->event_capacity * sizeof(MemoryTrace__MemoryEvent*));

    return writer;
}

void pb_trace_write_event(pb_trace_writer_t *writer,
                          uint64_t timestamp,
                          uint32_t thread_id,
                          uint64_t address,
                          bool is_write,
                          uint32_t size) {
    if (!writer) return;

    /* Resize array if needed */
    if (writer->event_count >= writer->event_capacity) {
        writer->event_capacity *= 2;
        writer->trace->events = (MemoryTrace__MemoryEvent**)realloc(
            writer->trace->events,
            writer->event_capacity * sizeof(MemoryTrace__MemoryEvent*));
    }

    /* Create new event */
    MemoryTrace__MemoryEvent *event =
        (MemoryTrace__MemoryEvent*)malloc(sizeof(MemoryTrace__MemoryEvent));
    memory_trace__memory_event__init(event);

    event->timestamp = timestamp;
    event->thread_id = thread_id;
    event->address = address;
    event->mem_op = is_write ? MEMORY_TRACE__MEM_OP__WRITE : MEMORY_TRACE__MEM_OP__READ;
    event->hit_miss = MEMORY_TRACE__HIT_MISS__MISS;  /* Can be updated if cache info available */

    writer->trace->events[writer->event_count++] = event;
    writer->trace->n_events = writer->event_count;
}

void pb_trace_writer_close(pb_trace_writer_t *writer) {
    if (!writer) return;

    /* Serialize protobuf to file */
    size_t packed_size = memory_trace__memory_trace__get_packed_size(writer->trace);
    uint8_t *buffer = (uint8_t*)malloc(packed_size);

    memory_trace__memory_trace__pack(writer->trace, buffer);
    fwrite(buffer, 1, packed_size, writer->file);

    free(buffer);

    /* Cleanup */
    for (size_t i = 0; i < writer->event_count; i++) {
        free(writer->trace->events[i]);
    }
    free(writer->trace->events);
    free(writer->trace);

    fclose(writer->file);
    free(writer);
}

/* ========== Time-Series Metrics Writer ========== */

pb_timeseries_writer_t* pb_timeseries_writer_create(
    const char *filename,
    const char *profiler,
    uint32_t pid,
    const char *command,
    uint32_t sample_window_refs,
    uint32_t cache_line_size) {

    pb_timeseries_writer_t *writer =
        (pb_timeseries_writer_t*)malloc(sizeof(pb_timeseries_writer_t));
    if (!writer) return NULL;

    writer->file = fopen(filename, "wb");
    if (!writer->file) {
        free(writer);
        return NULL;
    }

    /* Initialize time-series data */
    writer->data = (Memsys__Timeseries__TimeSeriesData*)
        malloc(sizeof(Memsys__Timeseries__TimeSeriesData));
    memsys__timeseries__time_series_data__init(writer->data);

    /* Initialize metadata */
    writer->data->metadata = (Memsys__Timeseries__RunMetadata*)
        malloc(sizeof(Memsys__Timeseries__RunMetadata));
    memsys__timeseries__run_metadata__init(writer->data->metadata);

    writer->data->metadata->profiler = strdup(profiler);
    writer->data->metadata->pid = pid;
    writer->data->metadata->command = strdup(command);
    writer->data->metadata->sample_window_refs = sample_window_refs;
    writer->data->metadata->cache_line_size = cache_line_size;
    writer->data->metadata->start_timestamp = 0;  /* Can be set later */
    writer->data->metadata->num_threads = 0;      /* Will be set before close */

    /* Pre-allocate sample array */
    writer->sample_capacity = 1024;
    writer->sample_count = 0;
    writer->data->samples = (Memsys__Timeseries__SampleWindow**)
        malloc(writer->sample_capacity * sizeof(Memsys__Timeseries__SampleWindow*));

    return writer;
}

void pb_timeseries_write_sample(pb_timeseries_writer_t *writer,
                                uint64_t window_number,
                                uint32_t thread_id,
                                uint64_t read_count,
                                uint64_t write_count,
                                uint64_t total_refs,
                                uint64_t wss_exact,
                                double wss_approx,
                                uint64_t timestamp) {
    if (!writer) return;

    /* Resize array if needed */
    if (writer->sample_count >= writer->sample_capacity) {
        writer->sample_capacity *= 2;
        writer->data->samples = (Memsys__Timeseries__SampleWindow**)realloc(
            writer->data->samples,
            writer->sample_capacity * sizeof(Memsys__Timeseries__SampleWindow*));
    }

    /* Create new sample */
    Memsys__Timeseries__SampleWindow *sample =
        (Memsys__Timeseries__SampleWindow*)malloc(sizeof(Memsys__Timeseries__SampleWindow));
    memsys__timeseries__sample_window__init(sample);

    sample->window_number = window_number;
    sample->thread_id = thread_id;
    sample->read_count = read_count;
    sample->write_count = write_count;
    sample->total_refs = total_refs;
    sample->wss_exact = wss_exact;
    sample->wss_approx = wss_approx;
    sample->timestamp = timestamp;

    writer->data->samples[writer->sample_count++] = sample;
    writer->data->n_samples = writer->sample_count;
}

void pb_timeseries_set_num_threads(pb_timeseries_writer_t *writer,
                                   uint32_t num_threads) {
    if (!writer || !writer->data->metadata) return;
    writer->data->metadata->num_threads = num_threads;
}

void pb_timeseries_writer_close(pb_timeseries_writer_t *writer) {
    if (!writer) return;

    /* Serialize protobuf to file */
    size_t packed_size = memsys__timeseries__time_series_data__get_packed_size(writer->data);
    uint8_t *buffer = (uint8_t*)malloc(packed_size);

    memsys__timeseries__time_series_data__pack(writer->data, buffer);
    fwrite(buffer, 1, packed_size, writer->file);

    free(buffer);

    /* Cleanup metadata */
    free((void*)writer->data->metadata->profiler);
    free((void*)writer->data->metadata->command);
    free(writer->data->metadata);

    /* Cleanup samples */
    for (size_t i = 0; i < writer->sample_count; i++) {
        free(writer->data->samples[i]);
    }
    free(writer->data->samples);
    free(writer->data);

    fclose(writer->file);
    free(writer);
}

#else /* !HAVE_PROTOBUF_C */

/* Stub implementations when protobuf-c is not available */

pb_trace_writer_t* pb_trace_writer_create(const char *filename) {
    fprintf(stderr, "Warning: Protobuf-c not available, trace output disabled\n");
    return NULL;
}

void pb_trace_write_event(pb_trace_writer_t *writer,
                          uint64_t timestamp, uint32_t thread_id,
                          uint64_t address, bool is_write, uint32_t size) {
    /* No-op */
}

void pb_trace_writer_close(pb_trace_writer_t *writer) {
    /* No-op */
}

pb_timeseries_writer_t* pb_timeseries_writer_create(
    const char *filename, const char *profiler, uint32_t pid,
    const char *command, uint32_t sample_window_refs,
    uint32_t cache_line_size) {
    fprintf(stderr, "Warning: Protobuf-c not available, time-series output disabled\n");
    return NULL;
}

void pb_timeseries_write_sample(pb_timeseries_writer_t *writer,
                                uint64_t window_number, uint32_t thread_id,
                                uint64_t read_count, uint64_t write_count,
                                uint64_t total_refs,
                                uint64_t wss_exact, double wss_approx,
                                uint64_t timestamp) {
    /* No-op */
}

void pb_timeseries_set_num_threads(pb_timeseries_writer_t *writer,
                                   uint32_t num_threads) {
    /* No-op */
}

void pb_timeseries_writer_close(pb_timeseries_writer_t *writer) {
    /* No-op */
}

#endif /* HAVE_PROTOBUF_C */
