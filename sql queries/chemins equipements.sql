-- Script à importer dans R3Web pour générer un csv à mettre dans data/
DECLARE @NomSite varchar(30) = 'US Open';
DECLARE @SiteId  int;
SELECT @SiteId = Id_lieu FROM Lieu WHERE Nom = @NomSite;

WITH LieuPath AS (

    -- Recursivite – le lieu racine (profondeur 0)
    SELECT
        Id_lieu                                               AS CurrentId, -- Id du lieu courant
        CAST(Nom AS nvarchar(4000))                           AS NomPath,   -- Chemin des noms de lieux (ex: Site>Lieu1>Lieu2)
        CAST(CAST(Id_lieu AS varchar(11)) AS nvarchar(4000))  AS IdPath,    -- Chemin des Id de lieux
        0                                                     AS Depth      -- Profondeur du lieu courant
    FROM Lieu
    WHERE Id_lieu = @SiteId

    UNION ALL

    -- Recursivite – les lieux enfants (profondeur 1, 2, …)
    SELECT
        L.Id_lieu,
        CAST(LP.NomPath + '>' + L.Nom                            AS nvarchar(4000)),
        CAST(LP.IdPath  + '>' + CAST(L.Id_lieu AS varchar(11))   AS nvarchar(4000)),
        LP.Depth + 1
    FROM      Lieu     L
    INNER JOIN LieuPath LP ON L.IdPere = LP.CurrentId
    WHERE LP.Depth < 16          -- maximum de 16 niveaux de profondeur

)
SELECT
    E.Nom      AS [Equipment Name],
    E.Id_Eqt   AS [Equipment ID],
    LP.Depth   AS [Path Length],
    LP.NomPath AS [Lieu Path],
    LP.IdPath  AS [ID Path]
FROM       Equipement E
INNER JOIN Type       T  ON E.Id_Type = T.Id_type
INNER JOIN LieuPath   LP ON E.Id_Lieu = LP.CurrentId
WHERE T.Categorie = 'E'
ORDER BY E.Nom
OPTION (MAXRECURSION 16);