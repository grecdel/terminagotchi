#!/usr/bin/env python3
"""Vérifie donnees/biomes.json : chaque variante de chaque espèce du bestiaire a un type de biome.

Usage : python3 donnees/verifier_biomes.py   (code de sortie 1 en cas d'erreur)
"""
import collections
import json
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))


def type_de(espece, variante, biomes, par_habitat):
    """Type de biome d'une variante (même règle que le jeu)."""
    if variante == 'classique':
        return biomes['classique_par_espece'].get(espece['id']) or biomes['classique_par_famille'].get(espece['famille'])
    return par_habitat.get(variante)


def main():
    biomes = json.load(open(os.path.join(ICI, 'biomes.json'), encoding='utf-8'))
    bestiaire = json.load(open(os.path.join(ICI, 'bestiaire2', 'bestiaire.json'), encoding='utf-8'))
    erreurs = []
    ids_types = [t['id'] for t in biomes['types']]
    if len(set(ids_types)) != len(ids_types):
        erreurs.append('id de type en double')
    par_habitat = {}
    for t in biomes['types']:
        for cle in ('id', 'nom', 'emoji', 'couleurs', 'sols', 'decors', 'habitats'):
            if not t.get(cle):
                erreurs.append(f"type {t.get('id')} : champ « {cle} » manquant")
        for h in t['habitats']:
            if h in par_habitat:
                erreurs.append(f"habitat « {h} » dans deux types : {par_habitat[h]} et {t['id']}")
            par_habitat[h] = t['id']
    if 'classique' in par_habitat:
        erreurs.append("« classique » ne doit pas être dans un type (il dépend de la famille)")
    familles = {e['famille'] for e in bestiaire}
    for f in sorted(familles - set(biomes['classique_par_famille'])):
        erreurs.append(f'famille sans type par défaut pour « classique » : {f}')
    for d in (biomes['classique_par_famille'], biomes['classique_par_espece']):
        for k, v in d.items():
            if v not in ids_types:
                erreurs.append(f'{k} → type inconnu « {v} »')
    ids_especes = {e['id'] for e in bestiaire}
    for k in biomes['classique_par_espece']:
        if k not in ids_especes:
            erreurs.append(f'classique_par_espece : espèce inconnue « {k} »')

    compte = collections.Counter()
    habitats_vus = set()
    for e in bestiaire:
        for v in e['variantes']:
            habitats_vus.add(v['id'])
            t = type_de(e, v['id'], biomes, par_habitat)
            if not t:
                erreurs.append(f"{e['id']} / {v['id']} : aucun type")
            else:
                compte[t] += 1
    for h in sorted(set(par_habitat) - habitats_vus):
        print(f'(info) habitat jamais utilisé par le bestiaire : {h}')

    if erreurs:
        print('ERREURS :')
        for x in erreurs:
            print(' -', x)
        sys.exit(1)
    total = sum(compte.values())
    print(f'OK : {len(bestiaire)} espèces, {total} variantes, toutes rangées dans {len(ids_types)} types.')
    for t in biomes['types']:
        print(f"  {t['emoji']} {t['nom']:<14} {compte[t['id']]:>4} variantes  ({', '.join(t['habitats'])})")


if __name__ == '__main__':
    main()
