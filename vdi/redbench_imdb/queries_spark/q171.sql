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
    n.name_pcode_nf IN ('B6525', 'F6534', 'I5353', 'M5342', 'M6215', 'O262', 'P6263', 'R2651', 'W4516')
  )
  AND (
    ci.note IN ('(contributing writer)', '(executive producer)') OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'director', 'miscellaneous crew', 'producer')
  )
  AND (
    it1.id IN ('25')
  )
