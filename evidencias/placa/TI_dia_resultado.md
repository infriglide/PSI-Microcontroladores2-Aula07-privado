Log: `../evidencias/placa/TI_dia.txt`

| ID | Teste | Resultado | Medido |
|---|---|---|---|
| TU-V1 | Veiculos: ordem verde > amarelo > vermelho | PASSOU | 21 transicoes corretas |
| TU-V2 | Veiculos: tempos 3 s / 1 s / 4 s | PASSOU | verde n=7, min=3001 ms, max=3002 ms; amarelo n=7, min=1002 ms, max=1012 ms; vermelho n=7, min=4016 ms, max=4017 ms |
| TU-V3 | Veiculos: exclusao mutua dos LEDs | PASSOU | 22 acendimentos, nunca dois LEDs juntos |
| TU-P2 | Pedestres: exclusao mutua dos LEDs | PASSOU | 15 acendimentos, nunca dois LEDs juntos |
| TI-1 | Nunca pedestre verde com carro verde/amarelo | PASSOU | 7 verdes de pedestre sem conflito; menor folga = 103 ms |
| TI-2 | Sincronismo pelo fio LIBERA_PED | PASSOU | 14 trocas; atraso medio 1 ms, maximo 3 ms (limite 150 ms) |
| TI-3 | Tempo do verde do pedestre (3,8 s) | PASSOU | verde do pedestre n=7, min=3805 ms, max=3807 ms (esperado 3800 ms) |
