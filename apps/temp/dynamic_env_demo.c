#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

extern char **environ;

void print_env_count() {
    int count = 0;
    for (char **env = environ; *env; env++, count++);
    printf("Environment variables: %d\n", count);
}

void print_test_var() {
    char *value = getenv("TEST_DYNAMIC");
    printf("TEST_DYNAMIC=%s\n", value ? value : "not set");
}

int main() {
    printf("=== Dynamic Environment Demo ===\n\n");
    
    printf("1. Initial state:\n");
    print_env_count();
    print_test_var();
    
    printf("\n2. Adding environment variable...\n");
    setenv("TEST_DYNAMIC", "hello_world", 1);
    print_env_count();
    print_test_var();
    
    printf("\n3. Modifying environment variable...\n");
    setenv("TEST_DYNAMIC", "modified_value", 1);
    print_env_count();
    print_test_var();
    
    printf("\n4. Adding another variable...\n");
    setenv("ANOTHER_VAR", "test123", 1);
    print_env_count();
    print_test_var();
    printf("ANOTHER_VAR=%s\n", getenv("ANOTHER_VAR"));
    
    printf("\n5. Removing variable...\n");
    unsetenv("TEST_DYNAMIC");
    print_env_count();
    print_test_var();
    
    return 0;
}