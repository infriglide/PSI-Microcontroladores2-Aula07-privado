Log: `../evidencias/placa/TS_botao.txt`

| ID | Teste | Resultado | Medido |
|---|---|---|---|
| TU-V1 | Veiculos: ordem verde > amarelo > vermelho | PASSOU | 15 transicoes corretas |
| TU-V2 | Veiculos: tempos 3 s / 1 s / 4 s | PASSOU | verde n=5, min=3001 ms, max=3002 ms; amarelo n=5, min=1002 ms, max=1002 ms; vermelho n=5, min=4016 ms, max=4019 ms |
| TU-V3 | Veiculos: exclusao mutua dos LEDs | PASSOU | 16 acendimentos, nunca dois LEDs juntos |
| TU-P2 | Pedestres: exclusao mutua dos LEDs | PASSOU | 11 acendimentos, nunca dois LEDs juntos |
| TI-1 | Nunca pedestre verde com carro verde/amarelo | PASSOU | 6 verdes de pedestre sem conflito; menor folga = 104 ms |
| TI-2 | Sincronismo pelo fio LIBERA_PED | PASSOU | 12 trocas; atraso medio 2 ms, maximo 4 ms (limite 150 ms) |
| TI-3 | Tempo do verde do pedestre (3,8 s) | PASSOU | verde do pedestre n=6, min=3804 ms, max=3806 ms (esperado 3800 ms) |
| TS-B1 | Botao com carros no verde/amarelo | PASSOU | 1 aperto(s); espera do pedestre: 138 ms (limite 2250 ms) |
| TS-B2 | Botao com pedestre ja verde | PASSOU | 2 aperto(s) ignorado(s), verde seguinte com 3 s |
