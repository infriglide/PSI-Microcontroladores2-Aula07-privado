"""
Roda o MESMO main.cpp das placas no computador (Linux/macOS), trocando a
API do Zephyr por uma imitacao simples (shim.h): threads viram threads do
sistema e os 3 fios entre as placas viram um arquivo compartilhado.
Serve para testar a logica antes de gravar na placa. NAO substitui o
teste na placa (nao tem GPIO real, nem tempo real do Zephyr).

Uso (dentro de testes/simulacao):  python3 simula.py
Gera os logs em ../../evidencias/simulacao e roda o verificador em cada um.
"""
import os, subprocess, sys, tempfile, threading

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.join(AQUI, "..", "..")
SAIDA = os.path.join(RAIZ, "evidencias", "simulacao")
sys.path.insert(0, os.path.join(AQUI, ".."))
import captura

def compila(placa, numero):
    fonte = open(os.path.join(RAIZ, placa, "src", "main.cpp")).read()
    fonte = fonte.replace("int main(void)", "int fw_main(void)")
    fonte += "\nint main(){ fw_main(); while(1) k_msleep(1000); }\n"
    cpp = os.path.join(tempfile.gettempdir(), f"sim_{placa}.cpp")
    exe = os.path.join(tempfile.gettempdir(), f"sim_{placa}")
    open(cpp, "w").write(fonte)
    subprocess.run(["g++", "-std=c++17", "-O1", "-pthread", f"-DPLACA={numero}",
                    "-I", AQUI, cpp, "-o", exe], check=True)
    return exe

def roda(nome, placas, roteiro, duracao, exes):
    fios = tempfile.mktemp(suffix=".bin")
    open(fios, "wb").write(b"\xff" * 16)       # 0xff = fio solto
    env = dict(os.environ, FIOS=fios)
    procs, fontes, enviar = [], [], {}
    for p in placas:
        pr = subprocess.Popen([exes[p]], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              env=env, bufsize=0)
        procs.append(pr)
        fontes.append(pr.stdout)
        enviar[p] = lambda letra, pr=pr: pr.stdin.write(letra.encode())
    arq = os.path.join(SAIDA, nome + ".txt")
    captura.captura(fontes, enviar, captura.le_roteiro(roteiro), duracao, arq)
    for pr in procs:
        pr.kill()
    return arq

CENARIOS = [
    ("sim_TU_veiculos", "v", "", 30),
    ("sim_TU_pedestres_autonomo", "p", "1:p:u,20:p:n,27:p:d", 45),
    ("sim_TU_pedestres_sem_mestre", "p", "", 12),
    ("sim_TI_TS_completo", "vp", "1.5:p:b,7.5:p:b,13.5:p:b,20.6:p:b,28:v:n,31:p:b,36:v:d", 52),
]

if __name__ == "__main__":
    os.makedirs(SAIDA, exist_ok=True)
    exes = {"v": compila("veiculos", 0), "p": compila("pedestres", 1)}
    arquivos = [None] * len(CENARIOS)
    def tarefa(i, c):
        arquivos[i] = roda(*c, exes)
    ths = [threading.Thread(target=tarefa, args=(i, c)) for i, c in enumerate(CENARIOS)]
    for t in ths: t.start()
    for t in ths: t.join()
    verif = os.path.join(AQUI, "..", "verifica_testes.py")
    for arq in arquivos:
        print("\n#####", os.path.basename(arq))
        subprocess.run([sys.executable, verif, arq, "--md", arq.replace(".txt", "_resultado.md")])
