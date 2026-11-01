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
    n.gender IN ('f', 'm')
  )
  AND (
    n.name_pcode_nf IN ('C1356', 'E1256', 'G564', 'H652', 'I5424', 'J3246', 'J4513', 'L545', 'P1236', 'P2435', 'P4526', 'R5632', 'S1616', 'S3154', 'T5')
  )
  AND (
    ci.note IN ('(archive footage)', '(series producer)', '(supervising producer)', '(voice)', '(writer)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'actress', 'cinematographer', 'producer', 'writer')
  )
  AND (
    it1.id IN ('25')
  )
