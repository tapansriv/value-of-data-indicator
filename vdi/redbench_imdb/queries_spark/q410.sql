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
    n.name_pcode_nf IN ('H6126', 'H6163', 'K2452', 'L6236', 'L6531', 'M5242', 'M6234', 'M6242', 'O2512', 'R2424', 'S5256', 'T5231', 'V5253')
  )
  AND (
    ci.note IN ('(as Herb Sargent)', '(uncredited)', '(voice)') OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'composer', 'director', 'writer')
  )
  AND (
    it1.id IN ('37')
  )
