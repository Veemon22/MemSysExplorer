# Common library for shared profiler utilities
cmake_minimum_required(VERSION 3.7)
project(profiler_common C CXX)

# Try to find protobuf
find_package(Protobuf QUIET)

# Always build the core utilities
set(CORE_SOURCES
    src/hll.c
    src/MurmurHash3.c
    src/ws_tsearch.c
    src/environment_capture.c
)

# Add protobuf sources if available
set(PROTOBUF_SOURCES "")
if(Protobuf_FOUND)
    # Generate C++ files from proto
    protobuf_generate_cpp(PROTO_SRCS PROTO_HDRS
        proto/memory_trace.proto
    )
    
    set(PROTOBUF_SOURCES 
        src/memory_trace.cpp
        ${PROTO_SRCS}
    )
    
    message(STATUS "Protobuf found - including memory trace support")
else()
    message(WARNING "Protobuf not found - memory trace support disabled")
    message(WARNING "Install protobuf development libraries to enable:")
    message(WARNING "  Ubuntu/Debian: sudo apt-get install libprotobuf-dev protobuf-compiler")
    message(WARNING "  CentOS/RHEL: sudo yum install protobuf-devel protobuf-compiler")
endif()

# Create static library for common utilities
add_library(profiler_common STATIC
    ${CORE_SOURCES}
    ${PROTOBUF_SOURCES}
)

# Set include directories
target_include_directories(profiler_common PUBLIC
    include
    ${CMAKE_CURRENT_BINARY_DIR}  # For generated protobuf headers
)

# Link libraries
if(Protobuf_FOUND)
    target_link_libraries(profiler_common ${Protobuf_LIBRARIES})
    target_compile_definitions(profiler_common PUBLIC HAVE_PROTOBUF=1)
endif()

# Link math library if on Unix (but not Apple)
if(UNIX AND NOT APPLE)
    target_link_libraries(profiler_common m)
endif()