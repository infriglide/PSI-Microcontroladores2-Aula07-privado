# Semáforos de Pedestres e Veículos: PSI Microcontroladores 2, Aula 07

**Repositório:** https://github.com/infriglide/PSI-Microcontroladores2-Aula07-privado

## Integrantes

| Nome | Nº USP | GitHub | Placa |
|---|---|---|---|
| Ingrid Beatriz Araujo de Oliveira | 14579120 | infriglide | Semáforo de veículos |
| Yara Joyce Moreno Rodrigues | 16905311 | yjmoreno | Semáforo de pedestres |

## Evolução do projeto

O trabalho foi feito em duas etapas, e as duas estão no repositório.

**1. Versões isoladas (Ingrid).** Cada parte do enunciado foi feita primeiro numa placa só, com LEDs externos na protoboard:

| Pasta | O que faz | Vídeo |
|---|---|---|
| `Atividade 1 Pedestre Ingrid/` | Pedestre com duas threads e um mutex, 4 s / 4 s | [exercício 1](https://github.com/user-attachments/assets/c2e6bf35-8c34-4ead-bebd-6eb302b51fee) |
| `Atividade 2 Veículo Ingrid/` | Veículos com três threads, um mutex e a variável `vez` para a ordem do ciclo | [exercício 2](https://github.com/user-attachments/assets/9bb6aab6-78d9-4922-be28-3c2ea587488d) |
| `Atividade 3 Modo Noturno Ingrid/` | Pedestre com botão que alterna o modo noturno (vermelho piscando) | [exercício 3](https://github.com/user-attachments/assets/c5c3e3a7-bcf3-4424-98c9-13f069875a76) |

Os vídeos estão com marca d'água porque precisaram ser comprimidos para caber no GitHub.

**2. Sistema integrado (Yara).** As pastas `veiculos/` e `pedestres/` juntam tudo: as duas placas ligadas por fios, o botão de travessia, o modo noturno nas duas placas e o plano de testes no modelo V. A ideia da variável `vez` e a pinagem vieram das versões da Ingrid.

## Requisitos

| ID | Requisito (do enunciado) |
|---|---|
| R1 | Pedestres: verde 4 s e vermelho 4 s, com duas threads e um mutex |
| R2 | Veículos: verde 3 s, amarelo 1 s e vermelho 4 s, com três threads e um mutex |
| R3 | Cada LED controlado por uma thread; nunca dois LEDs da mesma placa acesos juntos |
| R4 | Sincronismo entre os semáforos: pedestre nunca verde com os carros no verde ou no amarelo |
| R5 | Modo noturno: carros com amarelo piscando e pedestres com vermelho piscando, 1 s aceso e 1 s apagado |
| R6 | Botão de travessia: o pedestre fica verde e os carros são bloqueados de forma segura |
| R7 | Cada semáforo numa placa, de um integrante diferente |
| R8 | Estado seguro: se a ligação entre as placas falhar, o pedestre fica vermelho (requisito nosso, de segurança) |

## Visão geral

O sistema usa duas FRDM-KL25Z com Zephyr RTOS. A placa dos **veículos** é a mestre: ela faz o ciclo verde → amarelo → vermelho e avisa a placa dos **pedestres**, por um fio, quando o pedestre pode atravessar. A placa dos pedestres nunca decide sozinha ficar verde. Se o fio soltar ou a outra placa desligar, ela fica no vermelho, que é o estado seguro.

Os semáforos usam o LED RGB de cada placa, porque não tínhamos protoboard e LEDs na hora dos testes. Nos veículos, o amarelo é o vermelho e o verde do RGB acesos juntos. O código também funciona com LEDs externos, na mesma pinagem das versões da Ingrid: basta trocar `USA_LED_RGB` para 0 no `main.cpp`. O código foi escrito em C++, com uma classe `Led` pequena que guarda a porta e o pino, liga e desliga o LED e escreve no log toda vez que ele muda.

### Threads e mutex

| Placa | Thread | O que faz |
|---|---|---|
| Veículos | `thread_verde` | Acende o verde por 3 s (ou menos, se o botão for apertado) |
| Veículos | `thread_amarelo` | Acende o amarelo por 1 s; no modo noturno, pisca 1 s / 1 s |
| Veículos | `thread_vermelho` | Acende o vermelho por 4 s e libera o pedestre durante esse tempo |
| Veículos | `thread_entradas` | Lê o botão do modo noturno, o fio PEDIDO e os comandos da serial |
| Pedestres | `thread_verde` | Acende o verde enquanto o fio LIBERA_PED estiver em 1 |
| Pedestres | `thread_vermelho` | Acende o vermelho no resto do tempo; no modo noturno, pisca 1 s / 1 s |
| Pedestres | `thread_entradas` | Lê o botão de travessia e os comandos da serial |
| Pedestres | `thread_autonomo` | Só para o teste unitário: simula o fio LIBERA_PED com 4 s / 4 s |

Em cada placa, as threads dos LEDs disputam o mesmo `k_mutex`. Uma thread só acende o seu LED com o mutex na mão, e só solta o mutex depois de apagar. Assim, dois LEDs da mesma placa nunca ficam acesos ao mesmo tempo. Nos veículos, a ordem do ciclo vem da variável `vez` (VERDE, AMARELO ou VERMELHO), que também é protegida pelo mutex: a thread pega o mutex, confere se é a vez dela e, se não for, solta e tenta de novo depois de 5 ms. As variáveis lidas pelas entradas (`noite`, `pedido`) são `atomic_t`, para não precisar esperar o mutex, que pode ficar segurado por vários segundos.

### Sincronismo entre as placas

Durante os 4 s de vermelho dos carros, o fio LIBERA_PED fica em 1 por 3,8 s. Ele sobe 100 ms depois do vermelho acender e desce 100 ms antes do verde dos carros. Essa margem de 100 ms cobre o atraso de leitura da outra placa e garante que o pedestre já está vermelho quando os carros ficam verdes. Por isso, com as duas placas ligadas, o verde do pedestre dura 3,8 s em vez de 4 s. No teste unitário da placa de pedestres sozinha (modo autônomo), os tempos são exatamente 4 s / 4 s.

```
tempo (s)        0     0,1                     3,9  4,0          7,0      8,0
Carros         [ VERMELHO ......................... ][ VERDE 3 s  ][AMAR 1 s][ VERMELHO ...
LIBERA_PED     ________/‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\_____________________________/‾‾‾‾‾
Pedestres      [ VM ][ VERDE 3,8 s ................][ VERMELHO 4,2 s ...............][ VERDE
```

### Botão de travessia e modo noturno

Quando o botão é apertado, a placa de pedestres sobe o fio PEDIDO. Se os carros estiverem no verde há pelo menos 1 s, o verde é cortado na hora. Se o verde acabou de acender, ele espera completar 1 s, para não piscar. Em seguida vem **sempre** o amarelo de 1 s e depois o vermelho, então os carros nunca vão do verde direto para o vermelho. Se o pedestre já está verde, o pedido é ignorado. No modo noturno, o botão não faz nada.

O modo noturno é ligado e desligado pelo botão da placa de veículos (cada aperto alterna) ou pelos comandos `n` e `d` na serial. A placa de veículos repassa o modo para a de pedestres pelo fio NOITE. Os carros piscam o amarelo e os pedestres piscam o vermelho, 1 s aceso e 1 s apagado. Na volta ao dia, os carros recomeçam pelo vermelho.

## Montagem

| Componente | Placa de veículos | Placa de pedestres |
|---|---|---|
| Verde | RGB verde (PTB19) | RGB verde (PTB19) |
| Amarelo | RGB vermelho + verde (PTB18 + PTB19) | – |
| Vermelho | RGB vermelho (PTB18) | RGB vermelho (PTB18) |
| Botão (jumper encostado no GND) | D11 (PTD2): modo noturno, cada aperto alterna | D11 (PTD2): travessia |

Com LEDs externos (`USA_LED_RGB 0`): verde D2/D9, amarelo D3 e vermelho D5/D8, com o anodo no pino e um resistor de 220 a 330 Ω até o GND.

Ligações entre as placas, todas no header analógico:

| Sinal | Placa de veículos | Placa de pedestres | Sentido |
|---|---|---|---|
| LIBERA_PED | A0 (PTB0), saída | A0 (PTB0), entrada com pull-up | veículos → pedestres |
| NOITE | A1 (PTB1), saída | A1 (PTB1), entrada com pull-up | veículos → pedestres |
| PEDIDO | A3 (PTB3), entrada com pull-up | A3 (PTB3), saída | pedestres → veículos |
| GND | GND | GND | comum |

O A2 (PTB2) ficou de fora porque o devicetree da placa reserva esse pino para o ADC. Os três fios são **ativos em nível baixo**: o sinal vale quando o fio está em 0 V. As entradas usam o pull-up interno, então um fio solto fica em 3,3 V e é lido como "desligado": pedestre vermelho e modo dia. A primeira versão usava pull-down e sinal ativo em nível alto, mas na placa o A1 solto era lido como 1 (veja "Erros encontrados na placa"). Os botões usam o pull-up interno e não precisam de resistor. Um jumper encostado no GND já funciona como botão.

## Como compilar e gravar

Cada placa é um projeto PlatformIO separado (`veiculos/` e `pedestres/`). Abra a pasta da placa no VS Code e use **Upload and Monitor**. O monitor serial roda a 115200 baud.

| Comando na serial | Veículos | Pedestres |
|---|---|---|
| `n` / `d` | Modo noturno / modo dia | Só no modo autônomo |
| `b` | Pedido de travessia | Aperta o botão |
| `u` | (não usa) | Liga/desliga o modo autônomo |

Cada placa escreve uma linha por evento no formato `tempo_ms;PLACA;EVENTO`, por exemplo `8108;VEIC;VERMELHO_ON`. Esse log é a base de todos os testes.

## Plano de testes (modelo V)

Seguimos o modelo V do tutorial da disciplina: cada fase do desenvolvimento tem uma fase de teste correspondente.

| Fase de desenvolvimento | Neste projeto | Teste correspondente |
|---|---|---|
| 1. Requisitos | R1 a R8 | **Aceitação (TA)** |
| 2. Arquitetura | duas placas, três fios, modos dia, noite e travessia | **Sistema (TS)** |
| 3. Componentes | placa de veículos, placa de pedestres e a ligação entre elas | **Integração (TI)** |
| 4. Código | threads, mutex e classe `Led` de cada placa | **Unidade (TU)** |

Cada teste tem pré-condição (estado inicial), procedimento (as etapas) e resultado esperado (a pós-condição).

### Rastreabilidade

| Requisito | Testes que verificam |
|---|---|
| R1 | TU-P1, TU-P2 |
| R2 | TU-V1, TU-V2 |
| R3 | TU-V3, TU-P2, TU-V4 |
| R4 | TI-1, TI-2, TI-3 |
| R5 | TS-N1, TS-N2, TS-N3 |
| R6 | TS-B1, TS-B2, TS-B3, TS-B4 |
| R7 | TA-1 |
| R8 | TU-P3, TI-4 |

Os testes marcados como **auto** são conferidos pelo script `testes/verifica_testes.py`, que lê o log e dá PASSOU ou FALHOU com os tempos medidos. Os marcados como **visual** são conferidos olhando a placa e ficam registrados em vídeo. Para comparar eventos de placas diferentes, o `testes/captura.py` lê as duas portas seriais ao mesmo tempo e marca cada linha com o relógio do PC. As durações de um mesmo LED são medidas com o relógio da própria placa.

Tolerâncias usadas: ±50 ms para tempos medidos na placa e no máximo 150 ms de atraso entre as placas (fio + USB + PC).

### Testes unitários (cada semáforo isolado)

| ID | Requisito | Pré-condição | Procedimento | Resultado esperado | Verificação |
|---|---|---|---|---|---|
| TU-V1 | Ciclo dos carros | Só a placa de veículos ligada | Capturar 40 s de log | Ordem sempre verde → amarelo → vermelho → verde | auto |
| TU-V2 | Tempos dos carros | Igual ao TU-V1 | Mesmo log | Verde 3000 ms, amarelo 1000 ms, vermelho 4000 ms (±50 ms) | auto |
| TU-V3 | Mutex dos carros | Igual ao TU-V1 | Mesmo log | Nunca dois LEDs acesos juntos | auto |
| TU-V4 | LEDs físicos | Igual ao TU-V1 | Filmar a placa por um ciclo | Cada LED acende na ordem e no tempo do log; nunca dois acesos | visual |
| TU-P1 | Tempos dos pedestres | Só a placa de pedestres; comando `u` | Capturar 45 s com o roteiro `1:p:u` | Verde 4000 ms e vermelho 4000 ms, alternando (±50 ms) | auto |
| TU-P2 | Mutex dos pedestres | Igual ao TU-P1 | Mesmo log | Nunca verde e vermelho juntos | auto |
| TU-P3 | Estado seguro | Pedestres sem a outra placa e sem modo autônomo | Capturar 20 s | Pedestre só vermelho, nenhum verde | auto |

### Testes de integração (as duas placas juntas)

| ID | Requisito | Pré-condição | Procedimento | Resultado esperado | Verificação |
|---|---|---|---|---|---|
| TI-1 | Sem conflito entre semáforos | Placas ligadas pelos 3 fios + GND | Capturar 60 s das duas placas | Pedestre verde nunca junto com verde ou amarelo dos carros; folga ≥ 0 | auto |
| TI-2 | Sincronismo | Igual ao TI-1 | Mesmo log | Pedestre muda em até 150 ms depois do fio LIBERA_PED | auto |
| TI-3 | Tempo do pedestre no sistema | Igual ao TI-1 | Mesmo log | Verde do pedestre = 3800 ms (±50 ms) | auto |
| TI-4 | Fio solto | Sistema rodando | Tirar o fio LIBERA_PED durante o verde do pedestre | Pedestre vai para o vermelho e fica lá | visual |

### Testes de sistema (modos de operação)

| ID | Requisito | Pré-condição | Procedimento | Resultado esperado | Verificação |
|---|---|---|---|---|---|
| TS-N1 | Modo noturno | Sistema rodando | Roteiro `5:v:n,15:p:b,25:v:d` (noite aos 5 s, dia aos 25 s) | Carros só com o amarelo piscando, pedestres só com o vermelho piscando, 1 s / 1 s | auto |
| TS-N2 | Volta ao dia | Igual ao TS-N1 | Mesmo log | Primeiro LED dos carros depois do modo dia é o vermelho | auto |
| TS-N3 | Botão do modo noturno | Sistema rodando | Apertar o botão em D11 da placa de veículos duas vezes | Entra e sai do modo noturno; no log, cada `BOTAO_NOITE` vem seguido de `MODO_NOITE` ou `MODO_DIA` | visual + log |
| TS-B1 | Botão com carros no verde ou amarelo | Sistema no modo dia | Apertar o botão (ou `b`) com os carros no verde | Verde cortado (após 1 s mínimo), amarelo de 1 s, pedestre verde em até 2250 ms | auto |
| TS-B2 | Botão com pedestre já verde | Igual ao TS-B1 | Apertar com o pedestre verde | Pedido ignorado; o próximo verde dos carros dura 3 s | auto |
| TS-B3 | Botão no modo noturno | Modo noturno ativo | Apertar o botão | Nada muda | auto |
| TS-B4 | Botão físico | Sistema rodando | Apertar o botão em D11 da placa de pedestres | Mesmo comportamento do TS-B1, log com `BOTAO_FISICO` | auto + visual |

### Testes de aceitação (sistema completo contra o enunciado)

| ID | Pré-condição | Procedimento | Resultado esperado | Verificação |
|---|---|---|---|---|
| TA-1 | Duas placas ligadas, uma de cada integrante | Filmar 30 s de modo dia, apertar o botão de travessia, ligar e desligar o modo noturno | Todos os comportamentos de R1 a R6 aparecem no vídeo, sem nenhum conflito de LEDs | visual (vídeo) |
| TA-2 | Todos os TU, TI e TS executados na placa | Conferir a tabela de resultados | Todos os testes automáticos com PASSOU | tabela de resultados |

### Comandos para executar os testes

Dentro da pasta `testes/` (precisa do `pip install pyserial`). No Mac, as portas aparecem como `/dev/cu.usbmodemXXXX`.

```bash
# TU-V1..V3: so a placa de veiculos
python captura.py --veic PORTA_V --duracao 40 --saida ../evidencias/placa/TU_veiculos.txt

# TU-P1..P2: so a placa de pedestres, modo autonomo (e noite no meio)
python captura.py --ped PORTA_P --duracao 45 --roteiro "1:p:u,22:p:n,30:p:d" --saida ../evidencias/placa/TU_pedestres.txt

# TU-P3: so a placa de pedestres, sem modo autonomo
python captura.py --ped PORTA_P --duracao 20 --saida ../evidencias/placa/TU_pedestres_sem_mestre.txt

# TI-1..3: as duas placas ligadas, sem comandos
python captura.py --veic PORTA_V --ped PORTA_P --duracao 60 --saida ../evidencias/placa/TI_dia.txt

# TS-N1..N2 e TS-B3: noite aos 5 s, botao no meio da noite, dia aos 25 s
python captura.py --veic PORTA_V --ped PORTA_P --duracao 40 --roteiro "5:v:n,15:p:b,25:v:d" --saida ../evidencias/placa/TS_noturno.txt

# TS-B1..B2: varios apertos em momentos diferentes do ciclo
python captura.py --veic PORTA_V --ped PORTA_P --duracao 45 --roteiro "3:p:b,9:p:b,17:p:b,26:p:b,33:p:b" --saida ../evidencias/placa/TS_botao.txt

# depois de cada captura:
python verifica_testes.py ../evidencias/placa/TI_dia.txt --md ../evidencias/placa/TI_dia_resultado.md
```

Como as placas ligam em momentos diferentes, os apertos do roteiro caem em fases diferentes do ciclo. O verificador descobre sozinho em que estado os carros estavam em cada aperto e confere o caso certo (TS-B1, TS-B2 ou TS-B3). Se algum caso aparecer como "sem dados", é só rodar de novo.

### Validação do próprio verificador

Para saber se os testes realmente pegam erros, alteramos um log bom de propósito e rodamos o verificador de novo:

| Defeito injetado no log | Testes que falharam |
|---|---|
| Pedestre apaga o verde 300 ms atrasado | TU-P2, TI-1, TI-2, TI-3 |
| Verde dos carros com 3,5 s | TU-V2 |
| Amarelo acende antes do verde apagar (como se não houvesse mutex) | TU-V3 |
| Carros pulam o amarelo depois do botão | TU-V1, TS-B1 |

### Simulação antes da placa

Antes de gravar, rodamos o mesmo `main.cpp` das duas placas no computador. O arquivo `testes/simulacao/shim.h` imita a parte do Zephyr que o código usa: as threads viram threads do sistema operacional e os três fios viram um arquivo compartilhado entre os dois programas. O comando `python3 simula.py` (dentro de `testes/simulacao/`) compila, roda os cenários e chama o verificador. A simulação achou dois erros que corrigimos antes de ir para a placa:

| Erro encontrado | Teste que acusou | Correção |
|---|---|---|
| Com o pedestre já verde, o pulso do fio PEDIDO durava menos de 1 ms e a placa de veículos (que lê o fio a cada 20 ms) não via o pedido | TS-B2 (sem o evento `PEDIDO_IGNORADO`) | Pulso mínimo de 100 ms |
| Ao sair do modo noturno, o LED terminava a piscada atual, mas o ciclo já tinha começado a contar, e o primeiro vermelho ficava com 3 s | TU-P1 (vermelho de 3005 ms) | A piscada é interrompida assim que o modo dia volta |

A simulação não substitui o teste na placa, porque não tem GPIO real nem o escalonador do Zephyr. Ela serve para achar erros de lógica mais cedo.

## Erros encontrados na placa

| Erro | Teste que acusou | Causa | Correção |
|---|---|---|---|
| Pedestre sozinho piscava o vermelho (1 s / 1 s) em vez de ficar vermelho fixo | TU-P3 (`evidencias/placa/TU_pedestres_sem_mestre_falha_pulldown.txt`) | Com o fio NOITE solto, o pino A1 era lido como 1 mesmo com o pull-down interno, e a placa entrava no modo noturno sozinha | Fios passaram a ser ativos em nível baixo, com pull-up nas entradas (`GPIO_ACTIVE_LOW`); a simulação foi refeita e passou |

## Resultados

| ID | Simulação | Placa | Medido na placa | Evidência |
|---|---|---|---|---|
| TU-V1 | PASSOU | PASSOU | 14 transições corretas | `evidencias/placa/TU_veiculos.txt` |
| TU-V2 | PASSOU (verde 3003–3008, amarelo 1001–1004, vermelho 4002–4010 ms) | PASSOU | verde 3001–3002, amarelo 1002, vermelho 4016–4017 ms | `evidencias/placa/TU_veiculos.txt` |
| TU-V3 | PASSOU | PASSOU | 15 acendimentos, nunca dois juntos | `evidencias/placa/TU_veiculos.txt` |
| TU-V4 | (visual) | PASSOU | ciclo vermelho → verde → amarelo no vídeo | `evidencias/placa/TU_V4_veiculos.mp4` |
| TU-P1 | PASSOU (verde 4000–4001, vermelho 3999–4000 ms) | PASSOU | verde 3996–4000, vermelho 3997–3999 ms | `evidencias/placa/TU_pedestres.txt` |
| TU-P2 | PASSOU | PASSOU | 13 acendimentos, nunca dois juntos | `evidencias/placa/TU_pedestres.txt` |
| TU-P3 | PASSOU | PASSOU | 20 s, nenhum verde | `evidencias/placa/TU_pedestres_sem_mestre.txt` |
| TI-1 | PASSOU (menor folga 99 ms) | | | `evidencias/placa/TI_dia.txt` |
| TI-2 | PASSOU (atraso máx. 13 ms) | | | `evidencias/placa/TI_dia.txt` |
| TI-3 | PASSOU (3788–3806 ms) | | | `evidencias/placa/TI_dia.txt` |
| TI-4 | (visual) | | | vídeo |
| TS-N1 | PASSOU | PASSOU (só pedestres, modo autônomo) | vermelho: 3 piscadas de 1 s / 1 s | `evidencias/placa/TS_noturno.txt` |
| TS-N2 | PASSOU | | | `evidencias/placa/TS_noturno.txt` |
| TS-N3 | (visual) | | | vídeo |
| TS-B1 | PASSOU (espera do pedestre 696–1122 ms) | | | `evidencias/placa/TS_botao.txt` |
| TS-B2 | PASSOU | | | `evidencias/placa/TS_botao.txt` |
| TS-B3 | PASSOU | | | `evidencias/placa/TS_noturno.txt` |
| TS-B4 | (placa) | | | log + vídeo |
| TA-1 | (placa) | | | vídeo |
| TA-2 | – | | | esta tabela |

Os logs e as tabelas completas estão em `evidencias/simulacao/` e `evidencias/placa/`. Na placa, o TS-N1 foi feito primeiro só com a placa de pedestres; a versão com as duas placas entra junto com os testes de integração.

## Avaliação por pares

O sistema integrado entra no repositório por um Pull Request da branch `sistema-integrado`. A Ingrid revisa o código, roda os testes na placa de veículos e registra os comentários e a aprovação no próprio PR.

## Estrutura do repositório

| Pasta | Conteúdo |
|---|---|
| `Atividade 1/2/3 ... Ingrid/` | Versões isoladas de cada parte, com evidências |
| `veiculos/` | Projeto PlatformIO da placa de veículos (mestre) |
| `pedestres/` | Projeto PlatformIO da placa de pedestres |
| `testes/captura.py` | Captura o log das placas, com roteiro de comandos |
| `testes/verifica_testes.py` | Confere o log e dá o resultado de cada teste |
| `testes/simulacao/` | Imitação do Zephyr para rodar o código no computador |
| `evidencias/simulacao/` | Logs e resultados da simulação |
| `evidencias/placa/` | Logs, resultados e vídeos dos testes na placa |
| `docs/` | Resumo do modelo V e base teórica (semáforo e mutex) |

## Uso de IA generativa

Usamos o Claude (Anthropic) para ajudar a escrever o código inicial dos dois firmwares, os scripts de captura e verificação, a simulação e o rascunho deste plano de testes. A dupla revisou o código, conferiu os requisitos do enunciado, executou os testes nas placas e registrou as evidências.
