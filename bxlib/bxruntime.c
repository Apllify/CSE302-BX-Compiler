#include <sys/types.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h> 

void print_int(int64_t value) {
  (void) printf("%ld\n", value);
}

void print_bool(int64_t value) {
  (void) printf("%s\n", value ? "true" : "false");
}

// reminder : 
// - both arguments must be 8 bytes in size
void zero_out(void* address, size_t num_bytes) {
  memset(address, 0, num_bytes);
}

void* alloc(size_t num_bytes){
  return (malloc(num_bytes));
}

void* copy_array(void* dest, void* src, size_t n){
  return memcpy(dest, src, n);
}