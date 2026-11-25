"""
Captura o log serial das placas (uma ou duas ao mesmo tempo) e grava
num arquivo. Cada linha recebe o tempo do PC, que e o relogio comum
usado para comparar eventos entre as duas placas.

Formato gravado:  <tempo_pc_ms>;<tempo_placa_ms>;<PLACA>;<EVENTO>
Comandos enviados tambem sao gravados, como:  <tempo_pc_ms>;-;PC;CMD_<placa>_<letra>

Exemplos:
  # teste unitario dos veiculos (60 s, so uma placa)
  python captura.py --veic /dev/cu.usbmodem1102 --duracao 60 --saida ../evidencias/TU_veiculos.txt

  # teste do botao: aperta o botao (serial) aos 10 s e aos 30 s
  python captura.py --veic PORTA1 --ped PORTA2 --duracao 50 \
      --roteiro "10:p:b,30:p:b" --saida ../evidencias/TS_botao.txt

  Roteiro: lista "segundo:placa:letra" (placa v = veiculos, p = pedestres)

Precisa do pyserial:  pip install pyserial
"""

import argparse
import threading
import time

inicio = time.monotonic()
trava_arquivo = threading.Lock()


def agora_ms():
    return int((time.monotonic() - inicio) * 1000)


def grava(arq, linha):
    with trava_arquivo:
        arq.write(linha + "\n")
        arq.flush()
        print(linha)


def le_placa(fonte, arq, parar):
    """Le linhas de uma placa (porta serial ou qualquer objeto com readline)."""
    while not parar.is_set():
        bruto = fonte.readline()
        if not bruto:
            continue
        if isinstance(bruto, bytes):
            bruto = bruto.decode(errors="ignore")
        linha = bruto.strip()
        partes = linha.split(";")
        # so guarda linhas no formato do firmware: tempo;PLACA;EVENTO
        if len(partes) == 3 and partes[0].isdigit():
            grava(arq, f"{agora_ms()};{linha}")


def executa_roteiro(roteiro, enviar, arq, parar):
    """roteiro = [(segundo, placa, letra), ...]; enviar[placa](letra)"""
    for seg, placa, letra in sorted(roteiro):
        while agora_ms() < seg * 1000:
            if parar.is_set():
                return
            time.sleep(0.01)
        enviar[placa](letra)
        grava(arq, f"{agora_ms()};-;PC;CMD_{placa}_{letra}")


def le_roteiro(texto):
    roteiro = []
    if texto:
        for item in texto.split(","):
            seg, placa, letra = item.strip().split(":")
            roteiro.append((float(seg), placa, letra))
    return roteiro


def captura(fontes, enviar, roteiro, duracao, saida):
    """fontes = lista de objetos com readline(); enviar = {placa: funcao(letra)}"""
    global inicio
    inicio = time.monotonic()
    parar = threading.Event()
    with open(saida, "w") as arq:
        threads = [threading.Thread(target=le_placa, args=(f, arq, parar), daemon=True)
                   for f in fontes]
        threads.append(threading.Thread(target=executa_roteiro,
                                        args=(roteiro, enviar, arq, parar), daemon=True))
        for t in threads:
            t.start()
        try:
            time.sleep(duracao)
        except KeyboardInterrupt:
            pass
        parar.set()
        grava(arq, f"{agora_ms()};-;PC;FIM")
    print(f"\nLog salvo em {saida}")


def main():
    ap = argparse.ArgumentParser(description="Captura log das placas do semaforo")
    ap.add_argument("--veic", help="porta serial da placa de veiculos")
    ap.add_argument("--ped", help="porta serial da placa de pedestres")
    ap.add_argument("--duracao", type=float, default=60, help="segundos de captura")
    ap.add_argument("--roteiro", default="", help='ex.: "10:p:b,30:v:n"')
    ap.add_argument("--saida", required=True, help="arquivo de log")
    args = ap.parse_args()

    abertas = {p for p, porta in (("v", args.veic), ("p", args.ped)) if porta}
    if not abertas:
        ap.error("informe --veic e/ou --ped")
    if any(p not in abertas for _, p, _ in le_roteiro(args.roteiro)):
        ap.error("o roteiro usa uma placa que nao foi aberta")

    import serial  # pyserial

    fontes, enviar = [], {}
    for placa, porta in (("v", args.veic), ("p", args.ped)):
        if porta:
            s = serial.Serial(porta, 115200, timeout=0.1)
            s.reset_input_buffer()   # descarta sobras de capturas anteriores
            fontes.append(s)
            enviar[placa] = lambda letra, s=s: s.write(letra.encode())


    captura(fontes, enviar, le_roteiro(args.roteiro), args.duracao, args.saida)


if __name__ == "__main__":
    main()
