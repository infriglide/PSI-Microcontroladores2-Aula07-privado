/* ====================================================
 * PSI Microcontroladores 2 - Aula 07
 * Semaforo de VEICULOS (placa mestre)
 *
 * Tres threads, uma por LED (verde, amarelo, vermelho).
 * Um mutex garante que so uma delas mexe nos LEDs por vez,
 * e a variavel "vez" (protegida pelo mesmo mutex) diz de quem
 * e a vez: VERDE -> AMARELO -> VERMELHO -> VERDE ...
 *
 * LEDs: RGB da placa (USA_LED_RGB 1) ou externos (USA_LED_RGB 0,
 * anodo no pino, resistor de ~330 ohm ate o GND):
 *   verde D2 (PTD4), amarelo D3 (PTA12), vermelho D5 (PTA5)
 * Botao do modo noturno: D11 (PTD2) para o GND, cada aperto alterna
 * Fios para a placa de pedestres (ligar GND com GND):
 *   A0 (PTB0) SAIDA   LIBERA_PED : 1 = pedestre pode ficar verde
 *   A1 (PTB1) SAIDA   NOITE      : 1 = modo noturno
 *   A3 (PTB3) ENTRADA PEDIDO     : 1 = pedestre apertou o botao
 *
 * Comandos pela serial (115200): n = noite, d = dia, b = botao
 * Log pela serial: <tempo_ms>;VEIC;<evento>
 * ==================================================== */

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/sys/printk.h>
#include <zephyr/sys/atomic.h>

/* Tempos do enunciado (ms) */
#define T_VERDE       3000
#define T_AMARELO     1000
#define T_VERMELHO    4000
#define T_PISCA       1000   /* modo noturno: 1 s aceso, 1 s apagado */
#define MARGEM        100    /* folga de seguranca dentro do vermelho */
#define VERDE_MINIMO  1000   /* botao nao corta o verde antes disso */

#define STACK_SIZE 1024
#define PRIO_LED   5
#define PRIO_ENTR  4         /* entradas tem prioridade maior */

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
        printk("%u;VEIC;%s_ON\n", k_uptime_get_32(), nome);
    }
    void desligar() {
        gpio_pin_set(porta, pino, 0);
        if (pino2 >= 0) gpio_pin_set(porta, pino2, 0);
        printk("%u;VEIC;%s_OFF\n", k_uptime_get_32(), nome);
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
static Led led_amarelo("AMARELO", porta_b, RGB_VERMELHO, RGB_VERDE);
static Led led_vermelho("VERMELHO", porta_b, RGB_VERMELHO);
#else
static Led led_verde("VERDE", porta_d, 4);        /* D2  = PTD4  */
static Led led_amarelo("AMARELO", porta_a, 12);   /* D3  = PTA12 */
static Led led_vermelho("VERMELHO", porta_a, 5);  /* D5  = PTA5  */
#endif

/* Botao do modo noturno e fios de ligacao entre as placas */
#define PINO_BOTAO_NOITE 2   /* D11 = PTD2 */
#define PINO_LIBERA_PED  0   /* A0  = PTB0 */
#define PINO_NOITE       1   /* A1  = PTB1 */
#define PINO_PEDIDO      3   /* A3  = PTB3 */

/* ---------- estado compartilhado ---------- */
enum Vez { VEZ_VERDE, VEZ_AMARELO, VEZ_VERMELHO };

K_MUTEX_DEFINE(mutex_leds);         /* protege os LEDs e a variavel vez */
static Vez vez = VEZ_VERMELHO;      /* comeca no vermelho (estado seguro) */

static atomic_t noite  = ATOMIC_INIT(0);  /* 1 = modo noturno */
static atomic_t pedido = ATOMIC_INIT(0);  /* 1 = pedestre pediu travessia */
static atomic_t liberado = ATOMIC_INIT(0);/* 1 = pedestre esta liberado agora */

static void libera_pedestre(int valor)
{
    atomic_set(&liberado, valor);
    gpio_pin_set(porta_b, PINO_LIBERA_PED, valor);
    printk("%u;VEIC;LIBERA_PED_%s\n", k_uptime_get_32(), valor ? "ON" : "OFF");
}

/* Espera "ms" olhando o relogio a cada 10 ms (prazo absoluto, entao o
 * erro nao acumula). Volta antes se mudar para o modo noturno ou, no
 * verde, se o pedestre pediu travessia e o verde minimo ja passou. */
static void espera(uint32_t ms, bool para_com_pedido)
{
    uint32_t inicio = k_uptime_get_32();
    while (k_uptime_get_32() - inicio < ms) {
        if (atomic_get(&noite)) break;
        if (para_com_pedido && atomic_get(&pedido) &&
            k_uptime_get_32() - inicio >= VERDE_MINIMO) {
            printk("%u;VEIC;VERDE_CORTADO\n", k_uptime_get_32());
            break;
        }
        k_msleep(10);
    }
}

/* Espera ate ms milissegundos, mas volta antes se o modo noturno acabar */
static void espera_noite(uint32_t ms)
{
    uint32_t inicio = k_uptime_get_32();
    while (atomic_get(&noite) && k_uptime_get_32() - inicio < ms) k_msleep(10);
}

/* ---------- thread do LED verde ---------- */
void thread_verde(void *, void *, void *)
{
    while (1) {
        k_mutex_lock(&mutex_leds, K_FOREVER);
        if (!atomic_get(&noite) && vez == VEZ_VERDE) {
            led_verde.ligar();
            espera(T_VERDE, true);
            led_verde.desligar();
            vez = VEZ_AMARELO;
        }
        k_mutex_unlock(&mutex_leds);
        k_msleep(5);
    }
}

/* ---------- thread do LED amarelo ---------- */
void thread_amarelo(void *, void *, void *)
{
    while (1) {
        k_mutex_lock(&mutex_leds, K_FOREVER);
        if (atomic_get(&noite)) {
            /* modo noturno: so o amarelo pisca */
            led_amarelo.ligar();
            espera_noite(T_PISCA);
            led_amarelo.desligar();
            espera_noite(T_PISCA);
            vez = VEZ_VERMELHO;      /* ao voltar para o dia, comeca no vermelho */
        } else if (vez == VEZ_AMARELO) {
            led_amarelo.ligar();
            espera(T_AMARELO, false);
            led_amarelo.desligar();
            vez = VEZ_VERMELHO;
        }
        k_mutex_unlock(&mutex_leds);
        k_msleep(5);
    }
}

/* ---------- thread do LED vermelho ----------
 * Durante o vermelho dos carros o pedestre e liberado, mas so depois
 * de MARGEM ms, e e bloqueado de novo MARGEM ms antes do verde. */
void thread_vermelho(void *, void *, void *)
{
    while (1) {
        k_mutex_lock(&mutex_leds, K_FOREVER);
        if (!atomic_get(&noite) && vez == VEZ_VERMELHO) {
            led_vermelho.ligar();
            espera(MARGEM, false);
            if (!atomic_get(&noite)) {
                if (atomic_get(&pedido)) {
                    atomic_set(&pedido, 0);
                    printk("%u;VEIC;PEDIDO_ATENDIDO\n", k_uptime_get_32());
                }
                libera_pedestre(1);
                espera(T_VERMELHO - 2 * MARGEM, false);
                libera_pedestre(0);
                espera(MARGEM, false);
            }
            led_vermelho.desligar();
            vez = VEZ_VERDE;
        }
        k_mutex_unlock(&mutex_leds);
        k_msleep(5);
    }
}

/* ---------- entradas: chave, pedido do pedestre e serial ---------- */
static void muda_modo(int novo)
{
    if (atomic_get(&noite) == novo) return;
    atomic_set(&noite, novo);
    gpio_pin_set(porta_b, PINO_NOITE, novo);
    if (novo) {                                  /* pedestre bloqueado */
        atomic_set(&pedido, 0);
        atomic_set(&liberado, 0);
        gpio_pin_set(porta_b, PINO_LIBERA_PED, 0);
    }
    printk("%u;VEIC;MODO_%s\n", k_uptime_get_32(), novo ? "NOITE" : "DIA");
}

static void registra_pedido(const char *origem)
{
    if (atomic_get(&noite)) return;          /* sem travessia no modo noturno */
    if (atomic_get(&liberado)) {             /* pedestre ja esta verde */
        printk("%u;VEIC;PEDIDO_IGNORADO\n", k_uptime_get_32());
        return;
    }
    if (atomic_cas(&pedido, 0, 1)) {
        printk("%u;VEIC;PEDIDO_%s\n", k_uptime_get_32(), origem);
    }
}

void thread_entradas(void *, void *, void *)
{
    const device *uart = DEVICE_DT_GET(DT_CHOSEN(zephyr_console));
    int botao_ant = 0;
    int pedido_ant = 0;

    while (1) {
        /* botao do modo noturno (ativo em nivel baixo): cada aperto alterna.
         * Duas leituras com 20 ms de intervalo = sem trepidacao */
        int b1 = (gpio_pin_get(porta_d, PINO_BOTAO_NOITE) == 0);
        k_msleep(20);
        int b2 = (gpio_pin_get(porta_d, PINO_BOTAO_NOITE) == 0);
        int botao = b1 && b2;
        if (botao && !botao_ant) {
            printk("%u;VEIC;BOTAO_NOITE\n", k_uptime_get_32());
            muda_modo(!atomic_get(&noite));
        }
        botao_ant = botao;

        /* fio PEDIDO vindo da placa de pedestres (borda de subida) */
        int p = gpio_pin_get(porta_b, PINO_PEDIDO);
        if (p && !pedido_ant) registra_pedido("FIO");
        pedido_ant = p;

        /* comandos pela serial */
        unsigned char c;
        if (uart_poll_in(uart, &c) == 0) {
            if (c == 'n') muda_modo(1);
            else if (c == 'd') muda_modo(0);
            else if (c == 'b') registra_pedido("SERIAL");
        }
    }
}

K_THREAD_DEFINE(t_verde,    STACK_SIZE, thread_verde,    NULL, NULL, NULL, PRIO_LED, 0, 100);
K_THREAD_DEFINE(t_amarelo,  STACK_SIZE, thread_amarelo,  NULL, NULL, NULL, PRIO_LED, 0, 100);
K_THREAD_DEFINE(t_vermelho, STACK_SIZE, thread_vermelho, NULL, NULL, NULL, PRIO_LED, 0, 100);
K_THREAD_DEFINE(t_entradas, STACK_SIZE, thread_entradas, NULL, NULL, NULL, PRIO_ENTR, 0, 100);

int main(void)
{
    led_verde.iniciar();
    led_vermelho.iniciar();
    led_amarelo.iniciar();

    gpio_pin_configure(porta_b, PINO_LIBERA_PED, GPIO_OUTPUT_INACTIVE);
    gpio_pin_configure(porta_b, PINO_NOITE, GPIO_OUTPUT_INACTIVE);
    gpio_pin_configure(porta_b, PINO_PEDIDO, GPIO_INPUT | GPIO_PULL_DOWN);
    gpio_pin_configure(porta_d, PINO_BOTAO_NOITE, GPIO_INPUT | GPIO_PULL_UP);

    printk("%u;VEIC;INICIO\n", k_uptime_get_32());
    return 0;
}
