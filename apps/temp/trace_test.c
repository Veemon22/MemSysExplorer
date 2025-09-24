#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include "memory_trace.h"

int main() {
    printf("Testing Memory Trace Library\n");
    printf("============================\n");
    
    // Create a trace writer
    memory_trace_writer_t* writer = memory_trace_create_writer();
    if (!writer) {
        printf("Failed to create trace writer (protobuf not available)\n");
        printf("   Install protobuf with: sudo apt-get install libprotobuf-dev protobuf-compiler\n");
        return 1;
    }
    
    printf("Successfully created trace writer\n");
    
    // Simulate some memory operations
    printf("\nAdding sample memory events:\n");
    
    // Example: Program loading phase
    memory_trace_add_event(writer, 1000000, 123, 0x400000, MEM_READ, CACHE_MISS);  // Code read
    printf("   - 1000000ns: Thread 123 READ 0x400000 (MISS) - Loading code\n");
    
    memory_trace_add_event(writer, 1000100, 123, 0x401000, MEM_READ, CACHE_MISS);  // More code
    printf("   - 1000100ns: Thread 123 READ 0x401000 (MISS) - Loading more code\n");
    
    // Example: Data initialization
    memory_trace_add_event(writer, 1001000, 123, 0x600000, MEM_WRITE, CACHE_MISS); // First data write
    printf("   - 1001000ns: Thread 123 WRITE 0x600000 (MISS) - Initializing data\n");
    
    memory_trace_add_event(writer, 1001050, 123, 0x600040, MEM_WRITE, CACHE_HIT);  // Adjacent write
    printf("   - 1001050ns: Thread 123 WRITE 0x600040 (HIT) - Adjacent data\n");
    
    // Example: Hot loop execution
    memory_trace_add_event(writer, 1002000, 123, 0x400100, MEM_READ, CACHE_HIT);   // Loop instruction
    printf("   - 1002000ns: Thread 123 READ 0x400100 (HIT) - Loop instruction\n");
    
    memory_trace_add_event(writer, 1002010, 123, 0x600080, MEM_READ, CACHE_HIT);   // Array access
    printf("   - 1002010ns: Thread 123 READ 0x600080 (HIT) - Array access\n");
    
    memory_trace_add_event(writer, 1002020, 123, 0x600084, MEM_WRITE, CACHE_HIT);  // Array update
    printf("   - 1002020ns: Thread 123 WRITE 0x600084 (HIT) - Array update\n");
    
    // Example: Different thread activity
    memory_trace_add_event(writer, 1002500, 456, 0x700000, MEM_READ, CACHE_MISS);  // Thread 2
    printf("   - 1002500ns: Thread 456 READ 0x700000 (MISS) - Thread 2 activity\n");
    
    memory_trace_add_event(writer, 1002600, 456, 0x700100, MEM_WRITE, CACHE_MISS); // Thread 2 write
    printf("   - 1002600ns: Thread 456 WRITE 0x700100 (MISS) - Thread 2 write\n");
    
    // Example: Cache miss on larger stride
    memory_trace_add_event(writer, 1003000, 123, 0x608000, MEM_READ, CACHE_MISS);  // Large stride
    printf("   - 1003000ns: Thread 123 READ 0x608000 (MISS) - Large stride access\n");
    
    printf("\nTrace Statistics:\n");
    printf("   - Total events: %zu\n", memory_trace_get_event_count(writer));
    
    // Write to binary protobuf file
    printf("\nWriting trace to file:\n");
    if (memory_trace_write_to_file(writer, "/tmp/trace_output/sample_trace.pb") == 0) {
        printf("   - Binary trace written to /tmp/trace_output/sample_trace.pb\n");
    } else {
        printf("   - Failed to write binary trace to /tmp/trace_output/sample_trace.pb\n");
    }
    
    // Get buffer size and write to buffer
    int buffer_size = memory_trace_write_to_buffer(writer, NULL, 0);
    if (buffer_size > 0) {
        printf("   - Trace size: %d bytes\n", buffer_size);
        
        void* buffer = malloc(buffer_size);
        if (buffer && memory_trace_write_to_buffer(writer, buffer, buffer_size) > 0) {
            printf("   - Successfully serialized to memory buffer\n");
            
            // Show first few bytes as hex
            printf("   - First 16 bytes (hex): ");
            unsigned char* bytes = (unsigned char*)buffer;
            for (int i = 0; i < (buffer_size < 16 ? buffer_size : 16); i++) {
                printf("%02x ", bytes[i]);
            }
            printf("\n");
        }
        free(buffer);
    }
    
    // Clean up
    memory_trace_destroy_writer(writer);
    printf("\n Cleaned up resources\n");
    
    printf("\n How to read the trace:\n");
    printf("   - The .pb file is in Google Protocol Buffer binary format\n");
    printf("   - You can read it with any language that has protobuf support\n");
    printf("   - Use the schema in profilers/common/proto/memory_trace.proto\n");
    printf("   - Or use the C API to read: memory_trace_read_from_file() (if implemented)\n");
    
    return 0;
}