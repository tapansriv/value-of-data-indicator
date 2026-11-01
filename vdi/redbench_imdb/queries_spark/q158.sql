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
    n.gender IS NULL
  )
  AND (
    n.name_pcode_nf IN ('C235', 'I652', 'J562', 'M6362', 'N4526')
  )
  AND (
    ci.note IN ('(co-executive producer)', '(executive producer)', '(production assistant)', '(series producer)', '(trainee production assistant)')
  )
  AND (
    rt.role IN ('miscellaneous crew', 'producer')
  )
  AND (
    it1.id IN ('19')
  )
