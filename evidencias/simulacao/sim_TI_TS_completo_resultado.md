Log: `/home/claude/rep/testes/simulacao/../../evidencias/simulacao/sim_TI_TS_completo.txt`

| ID | Teste | Resultado | Medido |
|---|---|---|---|
| TU-V1 | Veiculos: ordem verde > amarelo > vermelho | PASSOU | 15 transicoes corretas |
| TU-V2 | Veiculos: tempos 3 s / 1 s / 4 s | PASSOU | verde n=3, min=3003 ms, max=3008 ms; amarelo n=2, min=1001 ms, max=1001 ms; vermelho n=5, min=4002 ms, max=4010 ms |
| TU-V3 | Veiculos: exclusao mutua dos LEDs | PASSOU | 21 acendimentos, nunca dois LEDs juntos |
| TU-P2 | Pedestres: exclusao mutua dos LEDs | PASSOU | 18 acendimentos, nunca dois LEDs juntos |
| TI-1 | Nunca pedestre verde com carro verde/amarelo | PASSOU | 6 verdes de pedestre sem conflito; menor folga = 99 ms |
| TI-2 | Sincronismo pelo fio LIBERA_PED | PASSOU | 12 trocas; atraso medio 2 ms, maximo 13 ms (limite 150 ms) |
| TI-3 | Tempo do verde do pedestre (3,8 s) | PASSOU | verde do pedestre n=5, min=3788 ms, max=3806 ms (esperado 3800 ms) |
| TS-N1 | Modo noturno: piscas de 1 s | PASSOU | VEIC amarelo: 3 piscadas; PED vermelho: 3 piscadas (1 s aceso / 1 s apagado) |
| TS-N2 | Volta ao dia pelo vermelho | PASSOU | 1 volta(s) ao dia comecando pelo vermelho |
| TS-B1 | Botao com carros no verde/amarelo | PASSOU | 3 aperto(s); espera do pedestre: 696, 1122, 1103 ms (limite 2250 ms) |
| TS-B2 | Botao com pedestre ja verde | PASSOU | 1 aperto(s) ignorado(s), verde seguinte com 3 s |
| TS-B3 | Botao no modo noturno | PASSOU | 1 aperto(s) no modo noturno sem efeito |
