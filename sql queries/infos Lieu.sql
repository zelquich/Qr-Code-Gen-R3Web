-- Script à importer dans R3Web pour générer le csv à mettre dans data/
SELECT L.Nom, L.Id_lieu, T.Categorie, T.Nom AS [Nom_Type]
FROM Lieu L
join Lieu S on S.Id_lieu = L.IdSite
join Type T on T.Id_Type = L.Id_Type
WHERE S.Nom = 'US Open' 
--AND (T.Categorie = 'R' OR T.Categorie = 'G') -- uncommenter cette ligne pour ne récupérer que les ensembles et sous ensembles
;