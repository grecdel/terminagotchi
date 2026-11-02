"""Le terminal du jeu : de courtes pages de manuel (man, whatis, apropos) pour les commandes qu'il connaît."""

RESUMES = {
    "ls": ("list directory contents", "ls [OPTION]... [FILE]...", "-a  all (hidden too)   -l  long listing   -R  recursive   -h  human sizes"),
    "cd": ("change the working directory", "cd [DIR]", "cd ~  home   cd ..  parent   cd -  previous directory"),
    "pwd": ("print name of current/working directory", "pwd", ""),
    "cat": ("concatenate files and print on the standard output", "cat [OPTION]... [FILE]...", "-n  number lines"),
    "cp": ("copy files and directories", "cp [OPTION]... SOURCE DEST", "-r  copy directories recursively"),
    "mv": ("move (rename) files", "mv [OPTION]... SOURCE DEST", ""),
    "rm": ("remove files or directories", "rm [OPTION]... [FILE]...", "-r  recursive   -f  force"),
    "mkdir": ("make directories", "mkdir [OPTION]... DIRECTORY...", "-p  make parent directories as needed"),
    "rmdir": ("remove empty directories", "rmdir DIRECTORY...", ""),
    "touch": ("change file timestamps (create empty files)", "touch FILE...", ""),
    "echo": ("display a line of text", "echo [-n] [-e] [STRING]...", ""),
    "grep": ("print lines that match patterns", "grep [OPTION]... PATTERNS [FILE]...",
             "-i  ignore case   -n  line numbers   -r  recursive   -c  count   -v  invert   -o  only matching"),
    "find": ("search for files in a directory hierarchy", "find [PATH]... [EXPRESSION]",
             "-name PATTERN   -type f|d   -size N   -newer FILE   -delete   -exec CMD {} \\;"),
    "head": ("output the first part of files", "head [-n NUM] [FILE]...", ""),
    "tail": ("output the last part of files", "tail [-n NUM] [-f] [FILE]...", ""),
    "wc": ("print newline, word, and byte counts for each file", "wc [-l] [-w] [-c] [FILE]...", ""),
    "sort": ("sort lines of text files", "sort [OPTION]... [FILE]...", "-n  numeric   -r  reverse   -u  unique   -k  key   -t  separator"),
    "uniq": ("report or omit repeated lines", "uniq [-c] [-d] [-u] [INPUT]", ""),
    "cut": ("remove sections from each line of files", "cut -d DELIM -f LIST [FILE]...", ""),
    "tr": ("translate or delete characters", "tr [-d] [-s] SET1 [SET2]", ""),
    "sed": ("stream editor for filtering and transforming text", "sed [-n] [-E] [-i] SCRIPT [FILE]...", "s/old/new/g   /re/d   Np"),
    "awk": ("pattern scanning and processing language", "awk [-F fs] [-v var=value] 'program' [FILE]...", ""),
    "chmod": ("change file mode bits", "chmod MODE FILE...", "644, 755, +x, u+w, go-r"),
    "less": ("view a file one screen at a time", "less FILE", "space: next page   b: back   /word: search   q: quit"),
    "tree": ("list contents of directories in a tree-like format", "tree [-a] [-d] [-L level] [DIR]", ""),
    "whoami": ("print effective user name", "whoami", ""),
    "date": ("print the system date and time", "date [+FORMAT]", ""),
    "sleep": ("delay for a specified amount of time", "sleep NUMBER[SUFFIX]", ""),
    "jobs": ("list the jobs of this shell", "jobs [-l]", ""),
    "kill": ("send a signal to a job", "kill [-SIGNAL] PID|%JOB", ""),
    "ps": ("report a snapshot of the current processes", "ps [aux]", "(dans le terminal du jeu : ses propres tâches)"),
    "du": ("estimate file space usage", "du [-s] [-h] [FILE]...", ""),
    "df": ("report file system space usage", "df [-h]", ""),
    "free": ("display amount of free and used memory", "free [-h]", ""),
    "diff": ("compare files line by line", "diff [-u] FILE1 FILE2", ""),
    "tar": ("an archiving utility", "tar czf ARCHIVE.tar.gz FILES...  |  tar xzf ARCHIVE.tar.gz", ""),
    "sha256sum": ("compute and check SHA256 message digest", "sha256sum [-c] [FILE]...", ""),
    "base64": ("base64 encode/decode data", "base64 [-d] [FILE]", ""),
    "xargs": ("build and execute command lines from standard input", "xargs [-0] [-n N] [COMMAND]", ""),
    "tee": ("read from standard input and write to standard output and files", "tee [-a] FILE...", ""),
    "seq": ("print a sequence of numbers", "seq [FIRST [INCREMENT]] LAST", ""),
    "sqlite3": ("A command line interface for SQLite", "sqlite3 [DATABASE] [SQL]", ""),
    "git": ("the stupid content tracker", "git COMMAND [ARGS]", "init, status, add, commit, log, diff"),
    "bc": ("An arbitrary precision calculator language", "bc [-l]", ""),
    "sh": ("command interpreter (shell)", "sh [FILE [ARGS]]", ""),
    "python3": ("an interpreted, interactive, object-oriented programming language",
                "python3 [-c command | file | -] [arg] ...",
                "(dans le terminal du jeu : le Python du jeu, seulement dans ton terrain ; pas de -m ni de pip)"),
    "curl": ("transfer a URL", "curl [options] <url>",
             "-I  head   -i  include   -s  silent   -v  verbose   -o FILE   -X METHOD   -d DATA   "
             "(dans le terminal du jeu : seulement le phare du Port, http://localhost:8042/)"),
    "alias": ("define or display aliases", "alias [NAME[='VALUE']]", ""),
    "man": ("an interface to the system reference manuals", "man PAGE", ""),
    "xxd": ("make a hex dump or do the reverse", "xxd [-b] [-p] [-r] [FILE]", ""),
    "od": ("dump files in octal and other formats", "od [-An] [-t TYPE] [-N BYTES] [FILE]", ""),
    "shuf": ("generate random permutations", "shuf [-n N] [FILE]", ""),
    "paste": ("merge lines of files", "paste [-d LIST] [FILE]...", ""),
    "rev": ("reverse lines characterwise", "rev [FILE]...", ""),
    "file": ("determine file type", "file FILE...", ""),
    "stat": ("display file status", "stat FILE...", ""),
    "test": ("check file types and compare values", "test EXPRESSION  |  [ EXPRESSION ]", ""),
    "export": ("set export attribute for shell variables", "export NAME[=VALUE]", ""),
}


def resume(cmd):
    r = RESUMES.get(cmd)
    return r[0] if r else None


def page_man(cmd):
    from . import outils
    r = RESUMES.get(cmd)
    if r is None:
        if cmd in outils.TOUS:
            r = (cmd, f"{cmd} [OPTION]... [FILE]...", "")
        else:
            return None
    titre = f"{cmd.upper()}(1)"
    lignes = [f"{titre:<39}User Commands{titre:>28}", "", "NAME", f"       {cmd} - {r[0]}", "", "SYNOPSIS",
              f"       {r[1]}", ""]
    if r[2]:
        lignes += ["OPTIONS", f"       {r[2]}", ""]
    lignes += ["NOTE", "       Le terminal du jeu Terminagotchi : une page courte. La page complète est dans un vrai",
               f"       terminal Linux (man {cmd}) ou sur https://man7.org.", ""]
    return "\n".join(lignes) + "\n"


def chercher(mot):
    return [f"{k:<15} (1)  - {v[0]}" for k, v in sorted(RESUMES.items()) if mot in k or mot in v[0]]
