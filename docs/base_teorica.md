# Base teórica: semáforos e mutex (livro 4.1.1.1 e 4.1.2.1)

Resumo das leituras pré-aula, usado no semáforo de pedestres e veículos. A versão completa, com o vídeo de Dekker e o jantar dos filósofos, está no documento de estudo da Aula 06 no Projeto do Claude ("estudo-aula06-dekker-semaforo-mutex").

## Os dois problemas de threads

| | Disputa | Coordenação |
|---|---|---|
| Pergunta | Duas threads mexendo no mesmo recurso estragam o resultado? | Uma thread precisa esperar algo que outra faz? |
| Objetivo | uma de cada vez (exclusão mútua) | avisar e esperar (sincronização) |
| Ferramenta | **mutex** | **semáforo** |

## Semáforo (4.1.1.1)

Um contador com uma fila de espera, gerenciado pelo núcleo.

| Operação | Zephyr | Efeito |
|---|---|---|
| criar | `K_SEM_DEFINE`, `k_sem_init` | valor inicial e máximo |
| esperar (take/pend) | `k_sem_take` | valor > 0: decrementa e segue; valor = 0: dorme na fila |
| sinalizar (give/post) | `k_sem_give` | acorda quem espera ou incrementa |

- Tipos: binário (0/1), contador (0..N) e de exclusão mútua (o mutex).
- Não tem dono: qualquer tarefa ou ISR pode dar `give`.
- Espera para sempre, com timeout ou sem esperar.

## Mutex (4.1.2.1)

Um semáforo binário especializado em exclusão mútua: uma chave com dono.

- Começa destravado. **Só quem travou pode destravar.**
- Trata **inversão de prioridade** por herança (quem segura o mutex herda a prioridade da tarefa mais importante que espera) ou por teto.
- Com vários mutexes: pegar sempre na mesma ordem e soltar na ordem inversa, para não dar deadlock.
- Não pode ser usado dentro de ISR.

## Semáforo × mutex

| | Semáforo | Mutex |
|---|---|---|
| Feito para | avisar eventos e contar | proteger seção crítica |
| Quem libera | qualquer um | só quem travou |
| Inversão de prioridade | não trata | trata |
| Uso em ISR | `give` sim | não |

## Problemas clássicos (vídeo de Dekker)

| Problema | O que é |
|---|---|
| Race condition | o resultado depende de quem chega primeiro; resolvida com exclusão mútua na seção crítica |
| Deadlock | cada um segura um recurso e espera o do outro, para sempre |
| Starvation | uma tarefa quase nunca consegue o recurso |

A "vez" do algoritmo de Dekker é a mesma ideia da variável `vez` do semáforo de veículos: decide de quem é o turno, enquanto o mutex garante que só uma thread mexe nos LEDs por vez.

## Ligação com a atividade

- Cada LED é uma thread; todas as threads de uma placa disputam o mesmo `k_mutex`. Só quem está com o mutex acende o seu LED, então dois LEDs nunca ficam acesos juntos.
- O mutex fica preso por segundos (o tempo do LED aceso), por isso as variáveis lidas pelas entradas (modo noturno, pedido do botão) são atômicas, para não precisar esperar o mutex.
