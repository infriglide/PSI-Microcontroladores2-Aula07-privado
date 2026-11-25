/* ====================================================
 * PSI Microcontroladores 2 - Aula 07
 * Semaforo de PEDESTRES
 *
 * Duas threads, uma por LED (verde e vermelho), com um mutex
 * para que os dois nunca fiquem acesos ao mesmo tempo.
 * Quem decide quando o pedestre pode atravessar e a placa dos
 * veiculos (fio LIBERA_PED). Sem esse sinal o pedestre fica
 * vermelho (estado seguro).
 *
 * LEDs: RGB da placa (USA_LED_RGB 1) ou externos (USA_LED_RGB 0,
 * anodo no pino, resistor de ~330 ohm ate o GND):
 *   verde D9 (PTD5), vermelho D8 (PTA13)
 * Botao de travessia: D11 (PTD2) para o GND
 * Fios para a placa de veiculos (ligar GND com GND):
 *   A0 (PTB0) ENTRADA LIBERA_PED : 1 = pode ficar verde
 *   A1 (PTB1) ENTRADA NOITE      : 1 = modo noturno
 *   A3 (PTB3) SAIDA   PEDIDO     : 1 = botao apertado
 *
 * Comandos pela serial (115200):
 *   b = botao
 *   u = liga/desliga modo autonomo (teste unitario, sem a outra placa)
 *   n / d = noite / dia (so no modo autonomo)
 * Log pela serial: <tempo_ms>;PED;<evento>
 * ==================================================== */

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/sys/printk.h>
#include <zephyr/sys/atomic.h>

#define T_PED        4000   /* modo autonomo: verde 4 s, vermelho 4 s */
#define T_PISCA      1000   /* modo noturno: 1 s aceso, 1 s apagado */
#define T_MAX_PEDIDO 15000  /* segura o fio PEDIDO no maximo 15 s */

#define STACK_SIZE 1024
#define PRIO_LED   5
#define PRIO_ENTR  4

static const device *const porta_a = DEVICE_DT_GET(DT_NODELABEL(gpioa));
static const device *const porta_b = DEVICE_DT_GET(DT_NODELABEL(gpiob));
static const device *const porta_d = DEVICE_DT_GET(DT_NODELABEL(gpiod));

/* Onde estao os LEDs:
 *   USA_LED_RGB 1 = LED RGB da propria placa (nao precisa de protoboard).
 *                   O RGB e ativo em nivel baixo: o pino em 0 acende.
 *   USA_LED_RGB 0 = LEDs externos na protoboard (anodo no pino, resistor ate o GND). */
#define USA_LED_RGB 1

/* ---------- classe simples para um LED ----------
 * Um "Led" pode ter dois pinos: no RGB, o amarelo e o vermelho
 * e o verde acesos juntos. */
class Led {
public:
    Led(const char *nome, const device *porta, int pino, int pino2 = -1)
        : nome(nome), porta(porta), pino(pino), pino2(pino2) {}

    void iniciar() {
        gpio_flags_t f = GPIO_OUTPUT_INACTIVE | (USA_LED_RGB ? GPIO_ACTIVE_LOW : 0);
        gpio_pin_configure(porta, pino, f);
        if (pino2 >= 0) gpio_pin_configure(porta, pino2, f);
    }
    void ligar() {
        gpio_pin_set(porta, pino, 1);
        if (pino2 >= 0) gpio_pin_set(porta, pino2, 1);
        printk("%u;PED;%s_ON\n", k_uptime_get_32(), nome);
    }
    void desligar() {
        gpio_pin_set(porta, pino, 0);
        if (pino2 >= 0) gpio_pin_set(porta, pino2, 0);
        printk("%u;PED;%s_OFF\n", k_uptime_get_32(), nome);
    }

private:
    const char *nome;
    const device *porta;
    int pino;
    int pino2;
};

#if USA_LED_RGB
#define RGB_VERMELHO 18   /* PTB18 */
#define RGB_VERDE    19   /* PTB19 */
static Led led_verde("VERDE", porta_b, RGB_VERDE);
static Led led_vermelho("VERMELHO", porta_b, RGB_VERMELHO);
#else
static Led led_verde("VERDE", porta_d, 5);        /* D9 = PTD5  */
static Led led_vermelho("VERMELHO", porta_a, 13); /* D8 = PTA13 */
#endif

/* Botao de travessia e fios de ligacao entre as placas */
#define PINO_BOTAO      2    /* D11 = PTD2 */
#define PINO_LIBERA_PED 0    /* A0  = PTB0 */
#define PINO_NOITE      1    /* A1  = PTB1 */
#define PINO_PEDIDO     3    /* A3  = PTB3 */

K_MUTEX_DEFINE(mutex_leds);

/* Modo autonomo: os sinais vem de variaveis em vez dos fios */
static atomic_t autonomo   = ATOMIC_INIT(0);
static atomic_t sim_libera = ATOMIC_INIT(0);
static atomic_t sim_noite  = ATOMIC_INIT(0);

static bool pode_atravessar()
{
    if (atomic_get(&autonomo)) return atomic_get(&sim_libera);
    return gpio_pin_get(porta_b, PINO_LIBERA_PED) == 1;
}

static bool modo_noite()
{
    if (atomic_get(&autonomo)) return atomic_get(&sim_noite);
    return gpio_pin_get(porta_b, PINO_NOITE) == 1;
}

/* Espera ate ms milissegundos, mas volta antes se o modo noturno acabar */
static void espera_noite(int ms)
{
    uint32_t inicio = k_uptime_get_32();
    while (modo_noite() && k_uptime_get_32() - inicio < (uint32_t)ms) k_msleep(10);
}

/* ---------- thread do LED verde ---------- */
void thread_verde(void *, void *, void *)
{
    while (1) {
        k_mutex_lock(&mutex_leds, K_FOREVER);
        if (!modo_noite() && pode_atravessar()) {
            led_verde.ligar();
            while (pode_atravessar() && !modo_noite()) k_msleep(2);
            led_verde.desligar();
        }
        k_mutex_unlock(&mutex_leds);
        k_msleep(2);
    }
}

/* ---------- thread do LED vermelho ---------- */
void thread_vermelho(void *, void *, void *)
{
    while (1) {
        k_mutex_lock(&mutex_leds, K_FOREVER);
        if (modo_noite()) {
            led_vermelho.ligar();
            espera_noite(T_PISCA);
            led_vermelho.desligar();
            espera_noite(T_PISCA);
        } else if (!pode_atravessar()) {
            led_vermelho.ligar();
            while (!pode_atravessar() && !modo_noite()) k_msleep(2);
            led_vermelho.desligar();
        }
        k_mutex_unlock(&mutex_leds);
        k_msleep(2);
    }
}

/* ---------- gerador do modo autonomo (so para o teste unitario) ---------- */
void thread_autonomo(void *, void *, void *)
{
    while (1) {
        if (atomic_get(&autonomo) && !atomic_get(&sim_noite)) {
            k_msleep(T_PED);
            atomic_set(&sim_libera, !atomic_get(&sim_libera));
        } else {
            atomic_set(&sim_libera, 0);
            k_msleep(10);
        }
    }
}

/* ---------- botao (fisico ou serial) e comandos ---------- */
static void pede_travessia(const char *origem)
{
    printk("%u;PED;BOTAO_%s\n", k_uptime_get_32(), origem);
    if (modo_noite() || atomic_get(&autonomo)) return;

    gpio_pin_set(porta_b, PINO_PEDIDO, 1);
    printk("%u;PED;PEDIDO_ON\n", k_uptime_get_32());
    k_msleep(100);   /* pulso minimo: a outra placa le o fio a cada 20 ms */
    int t = 100;
    while (!pode_atravessar() && !modo_noite() && t < T_MAX_PEDIDO) {
        k_msleep(10);
        t += 10;
    }
    gpio_pin_set(porta_b, PINO_PEDIDO, 0);
    printk("%u;PED;PEDIDO_OFF\n", k_uptime_get_32());
}

void thread_entradas(void *, void *, void *)
{
    const device *uart = DEVICE_DT_GET(DT_CHOSEN(zephyr_console));
    int apertado_ant = 0;

    while (1) {
        /* botao ativo em nivel baixo; duas leituras iguais = sem trepidacao */
        int b1 = (gpio_pin_get(porta_d, PINO_BOTAO) == 0);
        k_msleep(20);
        int b2 = (gpio_pin_get(porta_d, PINO_BOTAO) == 0);
        int apertado = b1 && b2;
        if (apertado && !apertado_ant) pede_travessia("FISICO");
        apertado_ant = apertado;

        unsigned char c;
        if (uart_poll_in(uart, &c) == 0) {
            if (c == 'b') {
                pede_travessia("SERIAL");
            } else if (c == 'u') {
                atomic_set(&autonomo, !atomic_get(&autonomo));
                atomic_set(&sim_noite, 0);
                printk("%u;PED;AUTONOMO_%s\n", k_uptime_get_32(),
                       atomic_get(&autonomo) ? "ON" : "OFF");
            } else if ((c == 'n' || c == 'd') && atomic_get(&autonomo)) {
                atomic_set(&sim_noite, c == 'n');
                printk("%u;PED;MODO_%s\n", k_uptime_get_32(), c == 'n' ? "NOITE" : "DIA");
            }
        }
    }
}

K_THREAD_DEFINE(t_verde,    STACK_SIZE, thread_verde,    NULL, NULL, NULL, PRIO_LED, 0, 100);
K_THREAD_DEFINE(t_vermelho, STACK_SIZE, thread_vermelho, NULL, NULL, NULL, PRIO_LED, 0, 100);
K_THREAD_DEFINE(t_autonomo, STACK_SIZE, thread_autonomo, NULL, NULL, NULL, PRIO_ENTR, 0, 100);
K_THREAD_DEFINE(t_entradas, STACK_SIZE, thread_entradas, NULL, NULL, NULL, PRIO_ENTR, 0, 100);

int main(void)
{
    led_verde.iniciar();
    led_vermelho.iniciar();

    /* pull-down: se o fio soltar, le 0 = pedestre vermelho, modo dia */
    gpio_pin_configure(porta_b, PINO_LIBERA_PED, GPIO_INPUT | GPIO_PULL_DOWN);
    gpio_pin_configure(porta_b, PINO_NOITE, GPIO_INPUT | GPIO_PULL_DOWN);
    gpio_pin_configure(porta_b, PINO_PEDIDO, GPIO_OUTPUT_INACTIVE);
    gpio_pin_configure(porta_d, PINO_BOTAO, GPIO_INPUT | GPIO_PULL_UP);

    printk("%u;PED;INICIO\n", k_uptime_get_32());
    return 0;
}
