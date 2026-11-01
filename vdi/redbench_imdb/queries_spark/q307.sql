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
    n.name_pcode_nf IN ('A2326', 'D1316', 'D136', 'D5252', 'H6432', 'K3416', 'K6251', 'M2415', 'M5242')
  )
  AND (
    ci.note IN ('(producer)') OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'cinematographer', 'composer', 'producer')
  )
  AND (
    it1.id IN ('26')
  )
