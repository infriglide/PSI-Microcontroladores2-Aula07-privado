Log: `../evidencias/placa/TS_noturno.txt`

| ID | Teste | Resultado | Medido |
|---|---|---|---|
| TU-V1 | Veiculos: ordem verde > amarelo > vermelho | PASSOU | 4 transicoes corretas |
| TU-V2 | Veiculos: tempos 3 s / 1 s / 4 s | PASSOU | verde n=1, min=3002 ms, max=3002 ms; amarelo n=1, min=1001 ms, max=1001 ms; vermelho n=1, min=4017 ms, max=4017 ms |
| TU-V3 | Veiculos: exclusao mutua dos LEDs | PASSOU | 16 acendimentos, nunca dois LEDs juntos |
| TU-P2 | Pedestres: exclusao mutua dos LEDs | PASSOU | 17 acendimentos, nunca dois LEDs juntos |
| TI-1 | Nunca pedestre verde com carro verde/amarelo | PASSOU | 3 verdes de pedestre sem conflito; menor folga = 105 ms |
| TI-2 | Sincronismo pelo fio LIBERA_PED | PASSOU | 6 trocas; atraso medio 1 ms, maximo 3 ms (limite 150 ms) |
| TI-3 | Tempo do verde do pedestre (3,8 s) | PASSOU | verde do pedestre n=2, min=3805 ms, max=3807 ms (esperado 3800 ms) |
| TS-N1 | Modo noturno: piscas de 1 s | PASSOU | VEIC amarelo: 9 piscadas; PED vermelho: 9 piscadas (1 s aceso / 1 s apagado) |
| TS-N2 | Volta ao dia pelo vermelho | PASSOU | 1 volta(s) ao dia comecando pelo vermelho |
| TS-B3 | Botao no modo noturno | PASSOU | 1 aperto(s) no modo noturno sem efeito |
