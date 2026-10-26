"""Refaz a animação do #306 do zero, pelo mesmo caminho do servidor (servidor.animar sem cena = primeira animação)."""
import os, shutil, subprocess, sys
P = "/srv/kitebiz/projetos/conteudo/estudio-v2"
pid = subprocess.run(["systemctl", "--user", "show", "-p", "MainPID", "--value", "newsbr360-estudio-v2"], capture_output=True, text=True).stdout.strip()
for kv in open(f"/proc/{pid}/environ", "rb").read().split(b"\0"):           # o mesmo ambiente do serviço (chaves, PATH)
    if b"=" in kv:
        k, v = kv.split(b"=", 1); os.environ.setdefault(k.decode(), v.decode())
os.chdir(P); sys.path.insert(0, P); sys.argv = [sys.argv[0], "4499"]
import estudio as E, servidor as S
a = E.pasta(306) / "animacao"; cena = a / "cena.html"
shutil.copy2(cena, a / "cena-antes-do-zero.html"); (a / "versoes").mkdir(exist_ok=True)
shutil.copy2(cena, a / "versoes" / "cena-antes-do-zero.html"); cena.unlink()
E.chat_add(306, "sistema", "Refazendo a animação do zero, com o roteiro e a voz de agora (uns 12 minutos). A cena anterior foi guardada.")
S.animar(306)
print("fim")
