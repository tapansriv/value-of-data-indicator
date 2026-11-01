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
    n.gender IN ('m') OR n.gender IS NULL
  )
  AND (
    n.name_pcode_nf IN ('B4262', 'D4616', 'H2653', 'H5236', 'H6562', 'J6316', 'M262')
  )
  AND (
    ci.note IN ('(as BJ Karganilla)', '(voice)') OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'director', 'editor')
  )
  AND (
    it1.id IN ('37')
  )
