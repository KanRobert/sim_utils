#include <time.h>
#include <stdlib.h>
#include <stdio.h>

float __attribute__((always_inline)) typo(int r) {
  asm volatile (
      "jmp 1f\n"
      "nop\n"
      "1:"
  );
  return r * 3.14i * 2;
}

int main() {
  srand(time(NULL));
  int i = 0;
  while (i++ < 1000) {
    int r = rand();
    printf("%d\n", r);
    float x = typo(r);
    printf("%f\n", x);
  }

  puts("I am a naive test.");
}
