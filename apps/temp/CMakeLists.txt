cmake_minimum_required(VERSION 3.7)
project(temp_tests C CXX)

# Add the common library
add_subdirectory(../profilers/common common)

# Include common headers
include_directories(../profilers/common/include)

# Create trace_test executable (uses protobuf memory trace library)
add_executable(trace_test trace_test.c)
target_link_libraries(trace_test profiler_common stdc++)

# Create dynamic_env_demo executable (simple C, uses standard library only)
add_executable(dynamic_env_demo dynamic_env_demo.c)
# This doesn't need profiler_common, it's standalone