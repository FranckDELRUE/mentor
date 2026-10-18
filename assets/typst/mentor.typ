// Bibliothèque d'impression commune à tous les Mentor.
// Un gabarit de discipline commence par :  #import "mentor.typ": *
// puis enveloppe son contenu dans  #show: mentor-page
// Les données arrivent dans donnees.json (écrit par le socle) ; les QR dans qr-<page>.svg.

#let donnees = json("donnees.json")
#let gris = luma(150)

#let mentor-page(corps) = {
  set document(title: donnees.titre, author: donnees.app.nom)
  set page(
    paper: "a4",
    margin: (top: 3.5cm, bottom: 2cm, x: 1.8cm),
    header-ascent: 0.5cm,
    header: context {
      let p = here().page()
      grid(
        columns: (1fr, auto),
        align: (left + horizon, right + horizon),
        gutter: 8pt,
        [
          #text(weight: "bold", size: 12pt)[#donnees.titre] \
          #text(size: 8.5pt, fill: luma(80))[#donnees.app.nom · #donnees.code · #donnees.eleve · #donnees.date#if donnees.at("duree_min", default: none) != none [ · #donnees.duree_min min]]
        ],
        image("qr-" + str(calc.min(p, donnees.qr_max)) + ".svg", height: 2.1cm),
      )
      line(length: 100%, stroke: 0.4pt + gris)
    },
    footer: context [
      #text(size: 8pt, fill: luma(100))[Ne pas écrire dans le carré du QR · ne pas plier la feuille]
      #h(1fr)
      #text(size: 8pt)[Page #here().page() / #counter(page).final().first()]
    ],
  )
  set text(lang: "fr", region: "FR", size: 11pt)
  set par(justify: true, leading: 0.62em)
  set heading(numbering: none)
  show heading.where(level: 2): set text(size: 12pt)
  corps
}

// Zones de réponse ---------------------------------------------------------------------------
#let interligne = 0.85cm

#let lignes(hauteur) = {
  let n = calc.max(1, int(hauteur / interligne))
  for i in range(n) {
    block(above: 0pt, below: 0pt, height: interligne, width: 100%, stroke: (bottom: 0.4pt + luma(170)))
  }
}

#let carreaux(hauteur) = block(
  height: hauteur, width: 100%,
  stroke: 0.4pt + luma(170),
  fill: tiling(size: (5mm, 5mm))[
    #place(line(start: (0%, 0%), end: (100%, 0%), stroke: 0.25pt + luma(205)))
    #place(line(start: (0%, 0%), end: (0%, 100%), stroke: 0.25pt + luma(205)))
  ],
)

#let cadre(hauteur) = block(height: hauteur, width: 100%, stroke: 0.6pt + gris, radius: 2pt)

#let zone-reponse(type: "lignes", hauteur_cm: 5) = {
  let h = hauteur_cm * 1cm
  v(4pt)
  if type == "lignes" { lignes(h) } else if type == "carreaux" { carreaux(h) } else { cadre(h) }
  v(8pt)
}

// Mise en forme -----------------------------------------------------------------------------
#let consigne(corps) = block(
  width: 100%, inset: 8pt, radius: 3pt, fill: luma(245), stroke: (left: 2pt + luma(120)), corps,
)

#let encadre(titre, corps) = block(
  width: 100%, inset: 10pt, radius: 3pt, stroke: 0.6pt + luma(120),
  [#text(weight: "bold")[#titre] \ #corps],
)

#let exercice(e, numero) = {
  block(breakable: true, width: 100%)[
    == Exercice #numero#if e.at("titre", default: "") != "" [ — #e.titre]#if e.at("bareme", default: none) != none [#h(1fr)#text(size: 9pt, weight: "regular")[(#e.bareme pts)]]

    #eval(e.enonce, mode: "markup")
  ]
  let r = e.at("reponse", default: none)
  if r != none { zone-reponse(type: r.at("type", default: "lignes"), hauteur_cm: r.at("hauteur_cm", default: 5)) }
}
