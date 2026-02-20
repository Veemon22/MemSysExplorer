#include <stdio.h>
#include <stdlib.h>
#include <math.h>

int main() {
    volatile double x = 0.0;

    for (long i = 0; i < 1000000000; i++) {
        x += sqrt(i);
    }

    printf("Done: %f\n", x);
    return 0;
}