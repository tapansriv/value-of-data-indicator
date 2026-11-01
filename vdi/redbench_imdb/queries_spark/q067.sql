SELECT
  COUNT(*)
FROM name AS n, aka_name AS an, info_type AS it1, person_info AS pi1, cast_info AS ci, role_type AS rt
WHERE
  n.id = ci.person_id
  AND ci.person_id = pi1.person_id
  AND it1.id = pi1.info_type_id
  AND n.id = pi1.person_id
  AND n.id = an.person_id
  AND ci.person_id = an.person_id
  AND an.person_id = pi1.person_id
  AND rt.id = ci.role_id
  AND (
    n.gender IN ('m')
  )
  AND (
    n.name_pcode_nf IN ('A3525', 'A4212', 'C2616', 'E3623', 'G16', 'H2536', 'H6353', 'K523', 'M2436', 'M3523', 'M4524', 'R2162', 'S3535', 'S3632', 'S526', 'T5625', 'W525', 'X1653')
  )
  AND (
    ci.note IN ('(director of photography)', '(producer)', '(voice)', '(writer)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'cinematographer', 'composer', 'producer', 'writer')
  )
  AND (
    it1.id IN ('32')
  )
