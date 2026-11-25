// Camada fake do Zephyr para rodar main.cpp no Linux (so para teste)
#pragma once
#include <cstdio>
#include <cstdint>
#include <atomic>
#include <mutex>
#include <thread>
#include <chrono>
#include <unistd.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <cstring>
#include <cstdlib>

struct device { char port; };
struct gpio_dt_spec { const device *port; int pin; int flags; };
static device dev_a{'A'}, dev_b{'B'}, dev_d{'D'}, dev_uart{'U'};
#define DEVGET_gpiob (&dev_b)
#define DT_ALIAS(x) x
#define DT_NODELABEL(x) x
#define DT_CHOSEN(x) x
#define DEVICE_DT_GET(x) DEVGET_(x)
#define DEVGET_(x) DEVGET_##x
#define DEVGET_gpioa (&dev_a)
#define DEVGET_gpiod (&dev_d)
#define DEVGET_zephyr_console (&dev_uart)
#define GPIO_DT_SPEC_GET(n, g) GSPEC_(n)
#define GSPEC_(n) SPEC_##n
#define SPEC_led0 {&dev_b, 19, 0}
#define SPEC_led2 {&dev_b, 18, 0}
#define GPIO_OUTPUT_INACTIVE 1
#define GPIO_INPUT 2
#define GPIO_PULL_UP 4
#define GPIO_PULL_DOWN 8
#define GPIO_ACTIVE_LOW 16
typedef int gpio_flags_t;

// redes compartilhadas entre os dois processos: -1 = ninguem dirigindo
static int8_t *redes() {
    static int8_t *m = nullptr;
    if (!m) { int fd = open(getenv("FIOS"), O_RDWR); m = (int8_t*)mmap(0, 16, PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0); }
    return m;
}
static int rede(const device *d, int pin) {
    if (d->port=='B' && pin==0) return 0;   // LIBERA_PED (A0)
    if (d->port=='B' && pin==1) return 1;   // NOITE (A1)
    if (d->port=='B' && pin==3) return 2;   // PEDIDO (A3)
    if (d->port=='D' && pin==2) return 3 + PLACA; // botao noite (veic) / travessia (ped)
    return -1;
}
static int pull_local[64];
inline int gpio_pin_configure(const device *d, int pin, int f) {
    int r = rede(d,pin); if (r<0) return 0;
    pull_local[r] = ((f & GPIO_PULL_UP) ? 1 : 0) ^ ((f & GPIO_ACTIVE_LOW) ? 1 : 0);
    if (f & GPIO_OUTPUT_INACTIVE) redes()[r] = 0;
    return 0;
}
inline int gpio_pin_set(const device *d, int pin, int v) { int r=rede(d,pin); if (r>=0) redes()[r]=v?1:0; return 0; }
inline int gpio_pin_get(const device *d, int pin) { int r=rede(d,pin); if (r<0) return 0; int v=redes()[r]; return v<0 ? pull_local[r] : v; }
inline int gpio_pin_configure_dt(const gpio_dt_spec *s, int f) { return 0; }
inline int gpio_pin_set_dt(const gpio_dt_spec *s, int v) { return 0; }

static auto t0 = std::chrono::steady_clock::now();
inline uint32_t k_uptime_get_32() { return std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now()-t0).count(); }
inline void k_msleep(int ms) { std::this_thread::sleep_for(std::chrono::milliseconds(ms)); }
#define printk(...) do { printf(__VA_ARGS__); fflush(stdout); } while(0)

inline int uart_poll_in(const device *, unsigned char *c) {
    static bool init = false; if (!init) { fcntl(0, F_SETFL, O_NONBLOCK); init = true; }
    return read(0, c, 1) == 1 ? 0 : -1;
}

struct k_mutex { std::mutex m; };
#define K_MUTEX_DEFINE(n) static k_mutex n
#define K_FOREVER 0
inline void k_mutex_lock(k_mutex *m, int) { m->m.lock(); }
inline void k_mutex_unlock(k_mutex *m) { m->m.unlock(); }

typedef std::atomic<long> atomic_t;
#define ATOMIC_INIT(v) {v}
inline long atomic_get(atomic_t *a) { return a->load(); }
inline long atomic_set(atomic_t *a, long v) { return a->exchange(v); }
inline bool atomic_cas(atomic_t *a, long o, long n) { return a->compare_exchange_strong(o, n); }

struct starter { starter(void(*f)(void*,void*,void*), int d) { std::thread([f,d]{ k_msleep(d); f(0,0,0); }).detach(); } };
#define K_THREAD_DEFINE(name, st, fn, a, b, c, prio, opt, delay) static starter name##_s(fn, delay)
