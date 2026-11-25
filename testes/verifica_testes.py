"""
Verifica automaticamente um log gravado pelo captura.py e mostra o
resultado de cada teste do plano (modelo V).

Uso:
  python verifica_testes.py ../evidencias/TI_dia.txt
  python verifica_testes.py ../evidencias/TI_dia.txt --md resultado.md

So roda os testes que fazem sentido para o log (ex.: um log so com a
placa de veiculos roda os testes unitarios dos veiculos). Os outros
aparecem como "sem dados".
"""

import argparse
import sys

# ---------- requisitos (iguais aos do firmware) ----------
T_VERDE, T_AMARELO, T_VERMELHO = 3000, 1000, 4000
T_PED = 4000          # pedestre no modo autonomo
T_PISCA = 1000
MARGEM = 100          # folga de seguranca dentro do vermelho dos carros
VERDE_MINIMO = 1000

TOL = 50              # tolerancia de tempo medido na propria placa (ms)
LAT = 150             # atraso maximo aceito entre placas (fio + USB + PC)
ACOMODA = 300         # tempo para acomodar depois de uma troca de modo


# ---------- leitura do log ----------
def le_log(caminho):
    eventos = []
    with open(caminho) as f:
        for linha in f:
            partes = linha.strip().split(";")
            if len(partes) != 4:
                continue
            pc, placa_ms, placa, ev = partes
            eventos.append({
                "pc": int(pc),
                "b": int(placa_ms) if placa_ms.isdigit() else None,
                "placa": placa,
                "ev": ev,
            })
    return eventos


def da_placa(eventos, placa):
    return [e for e in eventos if e["placa"] == placa]


def intervalos(eventos, placa, led):
    """Lista de periodos em que o LED ficou aceso."""
    lista, aberto = [], None
    for e in da_placa(eventos, placa):
        if e["ev"] == led + "_ON":
            aberto = e
        elif e["ev"] == led + "_OFF" and aberto:
            lista.append({"on_pc": aberto["pc"], "off_pc": e["pc"],
                          "on_b": aberto["b"], "off_b": e["b"],
                          "dur": e["b"] - aberto["b"]})
            aberto = None
    return lista


def janelas(eventos, placa, ev_inicio, ev_fim):
    """Periodos (em tempo do PC) entre dois eventos, ex.: MODO_NOITE -> MODO_DIA."""
    lista, ini = [], None
    fim_log = eventos[-1]["pc"] if eventos else 0
    for e in da_placa(eventos, placa):
        if e["ev"] == ev_inicio and ini is None:
            ini = e["pc"]
        elif e["ev"] == ev_fim and ini is not None:
            lista.append((ini, e["pc"]))
            ini = None
    if ini is not None:
        lista.append((ini, fim_log))
    return lista


def dentro(t, lista, folga=0):
    return any(a - folga <= t <= b + folga for a, b in lista)


def cruza(iv, lista, folga=0):
    """O intervalo encosta em alguma janela?"""
    return any(iv["on_pc"] <= b + folga and iv["off_pc"] >= a - folga for a, b in lista)


def trocas_de_modo(eventos):
    return [e["pc"] for e in eventos if e["ev"] in
            ("MODO_NOITE", "MODO_DIA", "AUTONOMO_ON", "AUTONOMO_OFF")]


def resumo_tempos(lista):
    if not lista:
        return "-"
    d = [i["dur"] for i in lista]
    return f"n={len(d)}, min={min(d)} ms, max={max(d)} ms"


# ---------- cada teste devolve (status, detalhe) ----------
SEM_DADOS = ("SEM DADOS", "")


def tu_v1_ordem(ev):
    """TU-V1: ordem verde -> amarelo -> vermelho -> verde (modo dia)."""
    veic = [e for e in da_placa(ev, "VEIC") if e["ev"].endswith("_ON")
            and e["ev"] in ("VERDE_ON", "AMARELO_ON", "VERMELHO_ON")]
    noite = janelas(ev, "VEIC", "MODO_NOITE", "MODO_DIA")
    proximo = {"VERDE_ON": "AMARELO_ON", "AMARELO_ON": "VERMELHO_ON",
               "VERMELHO_ON": "VERDE_ON"}
    trocas = trocas_de_modo(ev)
    n, erros = 0, []
    for a, b in zip(veic, veic[1:]):
        if dentro(a["pc"], noite) or dentro(b["pc"], noite):
            continue
        if any(a["pc"] <= t <= b["pc"] for t in trocas):
            continue
        n += 1
        if proximo[a["ev"]] != b["ev"]:
            erros.append(f"{a['ev']}->{b['ev']} em t={b['pc']} ms")
    if n < 3:
        return SEM_DADOS
    return ("PASSOU", f"{n} transicoes corretas") if not erros else ("FALHOU", "; ".join(erros[:3]))


def tu_v2_tempos(ev):
    """TU-V2: verde 3 s, amarelo 1 s, vermelho 4 s."""
    noite = janelas(ev, "VEIC", "MODO_NOITE", "MODO_DIA")
    cortes = [e["pc"] for e in ev if e["ev"] == "VERDE_CORTADO"]
    trocas = trocas_de_modo(ev)

    def normais(led):
        return [i for i in intervalos(ev, "VEIC", led)
                if not cruza(i, noite, ACOMODA)
                and not any(i["on_pc"] <= t <= i["off_pc"] + 20 for t in cortes)
                and not any(i["on_pc"] <= t <= i["off_pc"] for t in trocas)]

    v, a, r = normais("VERDE"), normais("AMARELO"), normais("VERMELHO")
    if not v or not a or not r:
        return SEM_DADOS
    ruins = [f"{nome} {i['dur']} ms" for nome, lst, alvo in
             (("verde", v, T_VERDE), ("amarelo", a, T_AMARELO), ("vermelho", r, T_VERMELHO))
             for i in lst if abs(i["dur"] - alvo) > TOL]
    det = f"verde {resumo_tempos(v)}; amarelo {resumo_tempos(a)}; vermelho {resumo_tempos(r)}"
    return ("PASSOU", det) if not ruins else ("FALHOU", "fora da tolerancia: " + ", ".join(ruins[:4]))


def exclusao(ev, placa, leds):
    """Nunca dois LEDs da mesma placa acesos juntos (tempo da propria placa)."""
    acesos, n, erros = set(), 0, []
    for e in da_placa(ev, placa):
        for led in leds:
            if e["ev"] == led + "_ON":
                acesos.add(led)
                n += 1
                if len(acesos) > 1:
                    erros.append(f"{sorted(acesos)} em t={e['b']} ms")
            elif e["ev"] == led + "_OFF":
                acesos.discard(led)
    if n == 0:
        return SEM_DADOS
    return ("PASSOU", f"{n} acendimentos, nunca dois LEDs juntos") if not erros \
        else ("FALHOU", "; ".join(erros[:3]))


def tu_v3_exclusao(ev):
    return exclusao(ev, "VEIC", ("VERDE", "AMARELO", "VERMELHO"))


def tu_p1_tempos_autonomo(ev):
    """TU-P1: pedestre sozinho (modo autonomo): verde 4 s, vermelho 4 s, alternando."""
    auto = janelas(ev, "PED", "AUTONOMO_ON", "AUTONOMO_OFF")
    if not auto:
        return SEM_DADOS
    noite = janelas(ev, "PED", "MODO_NOITE", "MODO_DIA")
    trocas = trocas_de_modo(ev)

    def validos(led):
        return [i for i in intervalos(ev, "PED", led)
                if dentro(i["on_pc"], auto) and dentro(i["off_pc"], auto)
                and not cruza(i, noite, ACOMODA)
                and not any(i["on_pc"] <= t <= i["off_pc"] for t in trocas)]

    v, r = validos("VERDE"), validos("VERMELHO")
    if not v or not r:
        return SEM_DADOS
    ruins = [f"{nome} {i['dur']} ms" for nome, lst in (("verde", v), ("vermelho", r))
             for i in lst if abs(i["dur"] - T_PED) > TOL]
    det = f"verde {resumo_tempos(v)}; vermelho {resumo_tempos(r)}"
    return ("PASSOU", det) if not ruins else ("FALHOU", ", ".join(ruins[:4]))


def tu_p2_exclusao(ev):
    return exclusao(ev, "PED", ("VERDE", "VERMELHO"))


def tu_p3_sem_mestre(ev):
    """TU-P3: sem a placa de veiculos (fio solto), pedestre fica so no vermelho."""
    if da_placa(ev, "VEIC") or janelas(ev, "PED", "AUTONOMO_ON", "AUTONOMO_OFF"):
        return SEM_DADOS
    ped = da_placa(ev, "PED")
    if not ped:
        return SEM_DADOS
    verdes = [e for e in ped if e["ev"] == "VERDE_ON"]
    duracao = (ev[-1]["pc"] - ev[0]["pc"]) / 1000
    if verdes:
        return ("FALHOU", f"pedestre ficou verde {len(verdes)}x sem a placa mestre")
    return ("PASSOU", f"{duracao:.0f} s de log, nenhum verde (estado seguro)")


def ti_1_seguranca(ev):
    """TI-1: pedestre verde nunca junto com verde/amarelo dos carros (tempo do PC)."""
    pv = intervalos(ev, "PED", "VERDE")
    carros = intervalos(ev, "VEIC", "VERDE") + intervalos(ev, "VEIC", "AMARELO")
    if not pv or not carros:
        return SEM_DADOS
    folga_min, erros = None, []
    for p in pv:
        for c in carros:
            if p["on_pc"] < c["off_pc"] and c["on_pc"] < p["off_pc"]:
                erros.append(f"conflito em t={max(p['on_pc'], c['on_pc'])} ms")
            else:
                folga = c["on_pc"] - p["off_pc"] if c["on_pc"] >= p["off_pc"] else p["on_pc"] - c["off_pc"]
                folga_min = folga if folga_min is None else min(folga_min, folga)
    if erros:
        return ("FALHOU", "; ".join(erros[:3]))
    return ("PASSOU", f"{len(pv)} verdes de pedestre sem conflito; menor folga = {folga_min} ms")


def ti_2_sincronismo(ev):
    """TI-2: pedestre acompanha o sinal LIBERA_PED da placa de veiculos."""
    lib_on = [e["pc"] for e in da_placa(ev, "VEIC") if e["ev"] == "LIBERA_PED_ON"]
    lib_off = [e["pc"] for e in da_placa(ev, "VEIC") if e["ev"] == "LIBERA_PED_OFF"]
    pv = intervalos(ev, "PED", "VERDE")
    if not lib_on or not pv:
        return SEM_DADOS
    atrasos, erros = [], []
    for t in lib_on:
        prox = [p for p in pv if p["on_pc"] >= t - 20]
        if not prox or prox[0]["on_pc"] - t > LAT:
            erros.append(f"pedestre nao ficou verde apos LIBERA em t={t} ms")
        else:
            atrasos.append(prox[0]["on_pc"] - t)
    for t in lib_off:
        abertos = [p for p in pv if p["on_pc"] < t <= p["off_pc"] + 20]
        for p in abertos:
            if p["off_pc"] - t > LAT:
                erros.append(f"verde do pedestre demorou {p['off_pc'] - t} ms para apagar")
            else:
                atrasos.append(max(0, p["off_pc"] - t))
    if erros:
        return ("FALHOU", "; ".join(erros[:3]))
    return ("PASSOU", f"{len(atrasos)} trocas; atraso medio {sum(atrasos) / len(atrasos):.0f} ms, "
                      f"maximo {max(atrasos)} ms (limite {LAT} ms)")


def ti_3_tempo_pedestre(ev):
    """TI-3: com as duas placas, verde do pedestre = vermelho dos carros - 2 x margem."""
    if not da_placa(ev, "VEIC"):
        return SEM_DADOS
    noite = janelas(ev, "VEIC", "MODO_NOITE", "MODO_DIA")
    v = [i for i in intervalos(ev, "PED", "VERDE") if not cruza(i, noite, ACOMODA)]
    if not v:
        return SEM_DADOS
    alvo = T_VERMELHO - 2 * MARGEM
    ruins = [i["dur"] for i in v if abs(i["dur"] - alvo) > TOL]
    det = f"verde do pedestre {resumo_tempos(v)} (esperado {alvo} ms)"
    return ("PASSOU", det) if not ruins else ("FALHOU", f"{det}; fora: {ruins[:4]}")


def piscas_ok(lista_iv, ini, fim):
    """Confere 1 s aceso / 1 s apagado dentro da janela [ini, fim]."""
    ivs = [i for i in lista_iv if i["on_pc"] >= ini + ACOMODA and i["off_pc"] <= fim]
    erros = [f"aceso {i['dur']} ms" for i in ivs if abs(i["dur"] - T_PISCA) > TOL]
    for a, b in zip(ivs, ivs[1:]):
        apagado = b["on_b"] - a["off_b"]
        if abs(apagado - T_PISCA) > TOL:
            erros.append(f"apagado {apagado} ms")
    return ivs, erros


def ts_n1_noturno(ev):
    """TS-N1: modo noturno -> carros: so amarelo piscando; pedestres: so vermelho piscando."""
    noite = janelas(ev, "VEIC", "MODO_NOITE", "MODO_DIA") or \
        janelas(ev, "PED", "MODO_NOITE", "MODO_DIA")
    if not noite:
        return SEM_DADOS
    erros, detalhes = [], []
    for ini, fim in noite:
        proibidos = [e for e in ev if ini + ACOMODA <= e["pc"] <= fim and e["ev"].endswith("_ON")
                     and (e["placa"], e["ev"]) not in (("VEIC", "AMARELO_ON"), ("PED", "VERMELHO_ON"))
                     and e["ev"] not in ("LIBERA_PED_ON", "PEDIDO_ON", "AUTONOMO_ON")]
        erros += [f"{e['placa']} {e['ev']} em t={e['pc']} ms" for e in proibidos]
        for placa, led in (("VEIC", "AMARELO"), ("PED", "VERMELHO")):
            if not da_placa(ev, placa):
                continue
            ivs, err = piscas_ok(intervalos(ev, placa, led), ini, fim)
            erros += [f"{placa} {x}" for x in err]
            if ivs:
                detalhes.append(f"{placa} {led.lower()}: {len(ivs)} piscadas")
    if erros:
        return ("FALHOU", "; ".join(erros[:4]))
    return ("PASSOU", "; ".join(detalhes) + " (1 s aceso / 1 s apagado)")


def ts_n2_volta_dia(ev):
    """TS-N2: ao voltar para o dia os carros recomecam pelo vermelho (seguro)."""
    voltas = [e["pc"] for e in da_placa(ev, "VEIC") if e["ev"] == "MODO_DIA"]
    if not voltas:
        return SEM_DADOS
    erros = []
    for t in voltas:
        prox = [e for e in da_placa(ev, "VEIC") if e["pc"] > t
                and e["ev"] in ("VERDE_ON", "AMARELO_ON", "VERMELHO_ON")]
        # o amarelo pode terminar a piscada em andamento; o primeiro LED novo de dia tem que ser vermelho
        prox = [e for e in prox if e["ev"] != "AMARELO_ON" or e["pc"] - t > 2 * T_PISCA + ACOMODA]
        if not prox:
            continue
        if prox[0]["ev"] != "VERMELHO_ON":
            erros.append(f"voltou com {prox[0]['ev']} em t={prox[0]['pc']} ms")
    if erros:
        return ("FALHOU", "; ".join(erros))
    return ("PASSOU", f"{len(voltas)} volta(s) ao dia comecando pelo vermelho")


def estado_carros(ev, t):
    """Qual LED dos carros estava aceso no instante t (tempo do PC)."""
    if dentro(t, janelas(ev, "VEIC", "MODO_NOITE", "MODO_DIA")):
        return "NOITE"
    if dentro(t, janelas(ev, "VEIC", "LIBERA_PED_ON", "LIBERA_PED_OFF")):
        return "PEDESTRE_VERDE"
    for led in ("VERDE", "AMARELO", "VERMELHO"):
        if any(i["on_pc"] <= t <= i["off_pc"] for i in intervalos(ev, "VEIC", led)):
            return led
    return "?"


def botoes(ev):
    return [e for e in da_placa(ev, "PED") if e["ev"].startswith("BOTAO_")]


def ts_b1_botao(ev):
    """TS-B1: botao com carros no verde/amarelo -> amarelo 1 s, vermelho, pedestre verde."""
    if not da_placa(ev, "VEIC"):
        return SEM_DADOS
    casos = [b for b in botoes(ev) if estado_carros(ev, b["pc"]) in ("VERDE", "AMARELO")]
    if not casos:
        return SEM_DADOS
    verdes = intervalos(ev, "VEIC", "VERDE")
    amarelos = intervalos(ev, "VEIC", "AMARELO")
    pv = intervalos(ev, "PED", "VERDE")
    erros, esperas = [], []
    for b in casos:
        t = b["pc"]
        # 1) se apertou no verde, o verde termina em no maximo (verde minimo) depois de acender
        v = [i for i in verdes if i["on_pc"] <= t <= i["off_pc"]]
        if v:
            fim_esperado = max(v[0]["on_pc"] + VERDE_MINIMO, t)
            if v[0]["off_pc"] - fim_esperado > LAT:
                erros.append(f"verde nao foi cortado (botao em t={t} ms)")
        # 2) depois do verde vem SEMPRE o amarelo de 1 s
        a = [i for i in amarelos if i["on_pc"] >= t - T_AMARELO - 20]
        if not a or abs(a[0]["dur"] - T_AMARELO) > TOL or a[0]["on_pc"] - t > VERDE_MINIMO + LAT:
            erros.append(f"sem amarelo de 1 s apos botao em t={t} ms")
        # 3) pedestre fica verde logo depois
        p = [i for i in pv if i["on_pc"] >= t]
        limite = VERDE_MINIMO + T_AMARELO + MARGEM + LAT
        if not p or p[0]["on_pc"] - t > limite:
            erros.append(f"pedestre nao ficou verde em {limite} ms (botao em t={t} ms)")
        else:
            esperas.append(p[0]["on_pc"] - t)
    if erros:
        return ("FALHOU", "; ".join(erros[:3]))
    return ("PASSOU", f"{len(casos)} aperto(s); espera do pedestre: "
                      f"{', '.join(str(x) for x in esperas)} ms (limite "
                      f"{VERDE_MINIMO + T_AMARELO + MARGEM + LAT} ms)")


def ts_b2_botao_ja_verde(ev):
    """TS-B2: botao com pedestre ja verde e ignorado e o ciclo continua normal."""
    casos = [b for b in botoes(ev) if estado_carros(ev, b["pc"]) == "PEDESTRE_VERDE"]
    if not casos:
        return SEM_DADOS
    ignorados = [e["pc"] for e in da_placa(ev, "VEIC") if e["ev"] == "PEDIDO_IGNORADO"]
    erros = []
    for b in casos:
        if not any(0 <= t - b["pc"] <= LAT for t in ignorados):
            erros.append(f"pedido nao foi ignorado (t={b['pc']} ms)")
        prox_verde = [i for i in intervalos(ev, "VEIC", "VERDE") if i["on_pc"] > b["pc"]]
        # se outro aperto cortou esse verde, a duracao dele nao vale para este caso
        if prox_verde and any(prox_verde[0]["on_pc"] <= o["pc"] <= prox_verde[0]["off_pc"]
                              for o in botoes(ev)):
            prox_verde = prox_verde[1:]
        if prox_verde and abs(prox_verde[0]["dur"] - T_VERDE) > TOL:
            erros.append(f"verde seguinte mudou para {prox_verde[0]['dur']} ms")
    if erros:
        return ("FALHOU", "; ".join(erros))
    return ("PASSOU", f"{len(casos)} aperto(s) ignorado(s), verde seguinte com 3 s")


def ts_b3_botao_noite(ev):
    """TS-B3: botao no modo noturno nao faz nada."""
    casos = [b for b in botoes(ev) if estado_carros(ev, b["pc"]) == "NOITE"]
    if not casos:
        return SEM_DADOS
    erros = []
    for b in casos:
        pedidos = [e for e in da_placa(ev, "VEIC") if e["ev"].startswith("PEDIDO_")
                   and e["ev"] != "PEDIDO_IGNORADO" and 0 <= e["pc"] - b["pc"] <= 2000]
        if pedidos:
            erros.append(f"pedido aceito no modo noturno (t={b['pc']} ms)")
    if erros:
        return ("FALHOU", "; ".join(erros))
    return ("PASSOU", f"{len(casos)} aperto(s) no modo noturno sem efeito")


TESTES = [
    ("TU-V1", "Veiculos: ordem verde > amarelo > vermelho", tu_v1_ordem),
    ("TU-V2", "Veiculos: tempos 3 s / 1 s / 4 s", tu_v2_tempos),
    ("TU-V3", "Veiculos: exclusao mutua dos LEDs", tu_v3_exclusao),
    ("TU-P1", "Pedestres (autonomo): tempos 4 s / 4 s", tu_p1_tempos_autonomo),
    ("TU-P2", "Pedestres: exclusao mutua dos LEDs", tu_p2_exclusao),
    ("TU-P3", "Pedestres sem placa mestre: fica vermelho", tu_p3_sem_mestre),
    ("TI-1", "Nunca pedestre verde com carro verde/amarelo", ti_1_seguranca),
    ("TI-2", "Sincronismo pelo fio LIBERA_PED", ti_2_sincronismo),
    ("TI-3", "Tempo do verde do pedestre (3,8 s)", ti_3_tempo_pedestre),
    ("TS-N1", "Modo noturno: piscas de 1 s", ts_n1_noturno),
    ("TS-N2", "Volta ao dia pelo vermelho", ts_n2_volta_dia),
    ("TS-B1", "Botao com carros no verde/amarelo", ts_b1_botao),
    ("TS-B2", "Botao com pedestre ja verde", ts_b2_botao_ja_verde),
    ("TS-B3", "Botao no modo noturno", ts_b3_botao_noite),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--md", help="grava o resultado numa tabela markdown")
    args = ap.parse_args()

    ev = le_log(args.log)
    if not ev:
        sys.exit("log vazio ou em formato errado")

    linhas, falhou = [], False
    for tid, nome, func in TESTES:
        status, det = func(ev)
        falhou |= status == "FALHOU"
        linhas.append((tid, nome, status, det))
        if status != "SEM DADOS":
            print(f"{tid:6} {status:7} {nome}\n         {det}")

    if args.md:
        with open(args.md, "w") as f:
            f.write(f"Log: `{args.log}`\n\n| ID | Teste | Resultado | Medido |\n|---|---|---|---|\n")
            for tid, nome, status, det in linhas:
                if status != "SEM DADOS":
                    f.write(f"| {tid} | {nome} | {status} | {det} |\n")
    sys.exit(1 if falhou else 0)


if __name__ == "__main__":
    main()
