// Gabarit générique : consignes + exercices + zones de réponse.
// Une discipline le remplace en plaçant son propre feuille.typ (ou <type>.typ) dans templates/.
#import "mentor.typ": *
#show: mentor-page

#let c = donnees.contenu
#if c.at("consignes", default: "") != "" { consigne(eval(c.consignes, mode: "markup")) }

#for (i, e) in c.at("exercices", default: ()).enumerate() { exercice(e, i + 1) }
