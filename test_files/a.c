#include <time.h>
#include <stdlib.h>
#include <stdio.h>

int main() {
  srand(time(NULL));
  int i = 0;
  while (i++ < 1000) {
    int r = rand();
    printf("%d\n", r);
    float x = r * 3.14i * 2;
    printf("%f\n", x);
  }

  puts("I am a naive test.");
}
