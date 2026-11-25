Log: `../evidencias/placa/TS_botao.txt`

| ID | Teste | Resultado | Medido |
|---|---|---|---|
| TU-V1 | Veiculos: ordem verde > amarelo > vermelho | PASSOU | 16 transicoes corretas |
| TU-V2 | Veiculos: tempos 3 s / 1 s / 4 s | PASSOU | verde n=2, min=3002 ms, max=3002 ms; amarelo n=6, min=1002 ms, max=1002 ms; vermelho n=5, min=4016 ms, max=4020 ms |
| TU-V3 | Veiculos: exclusao mutua dos LEDs | PASSOU | 17 acendimentos, nunca dois LEDs juntos |
| TU-P2 | Pedestres: exclusao mutua dos LEDs | PASSOU | 10 acendimentos, nunca dois LEDs juntos |
| TI-1 | Nunca pedestre verde com carro verde/amarelo | PASSOU | 4 verdes de pedestre sem conflito; menor folga = 104 ms |
| TI-2 | Sincronismo pelo fio LIBERA_PED | FALHOU | pedestre nao ficou verde apos LIBERA em t=34155 ms; pedestre nao ficou verde apos LIBERA em t=42182 ms |
| TI-3 | Tempo do verde do pedestre (3,8 s) | FALHOU | verde do pedestre n=4, min=3804 ms, max=83804 ms (esperado 3800 ms); fora: [83804] |
| TS-B1 | Botao com carros no verde/amarelo | FALHOU | pedestre nao ficou verde em 2250 ms (botao em t=33022 ms) |
| TS-B2 | Botao com pedestre ja verde | FALHOU | verde seguinte mudou para 2741 ms |
