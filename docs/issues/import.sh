#!/bin/bash
# Cria labels e issues no repo atual via gh CLI. Rode na raiz do repo GitHub.
# Uso: bash docs/issues/import.sh
set -e
for s in 0 1 2 3 4 5 6 7 8; do gh label create "sprint-$s" --color 1D76DB 2>/dev/null || true; done
for st in "status:pronto" "status:parcial" "status:a-fazer"; do gh label create "$st" --color 0E8A16 2>/dev/null || true; done
for md in docs/issues/s*.md; do
  title=$(head -1 "$md" | sed 's/^# //')
  sprint=$(echo "$md" | grep -o 's[0-9]' | head -1)
  status=$(grep -m1 'Status no MVP' "$md" | grep -o 'done\|partial\|pending')
  case "$status" in
    done) lbl="status:pronto";; partial) lbl="status:parcial";; *) lbl="status:a-fazer";;
  esac
  gh issue create --title "$title" --body-file "$md" --label "$sprint,$lbl"
done
