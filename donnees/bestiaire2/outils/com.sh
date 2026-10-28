#!/bin/sh
# com.sh "message" : commit des seules images de variantes, puis push
cd /home/claude/depot-android && git add donnees/bestiaire2/images && git -c user.name="Claude" -c user.email="noreply@anthropic.com" commit -qm "$1 [skip ci]

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01Divag9b9e52aPY37DGRpjJ" -- donnees/bestiaire2/images && git pull -q --rebase --autostash 2>/dev/null; git push -q && git log --oneline -1
