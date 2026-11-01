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
    n.gender IN ('f') OR n.gender IS NULL
  )
  AND (
    n.name_pcode_nf IN ('B6245', 'C6452', 'D6262', 'M2423', 'S6154', 'Z3526')
  )
  AND (
    ci.note IN ('(production coordinator)') OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actress', 'miscellaneous crew', 'writer')
  )
  AND (
    it1.id IN ('26')
  )
