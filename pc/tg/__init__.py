import os as _os

if _os.environ.get("TG_ARRET"):
    # Lancé par le terminal du jeu sous Windows (vsh/outils.lancer_programme) : Windows n'a pas de SIGINT à envoyer à
    # un autre programme ; le terminal pose alors ce petit fichier, et le jeu s'arrête comme avec Ctrl+C.
    def _guetter(f=_os.environ.pop("TG_ARRET")):
        import _thread
        import time
        while not _os.path.exists(f):
            time.sleep(0.1)
        _thread.interrupt_main()

    import threading as _threading
    _threading.Thread(target=_guetter, daemon=True).start()
