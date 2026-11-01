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
    n.gender IN ('f', 'm') OR n.gender IS NULL
  )
  AND (
    n.name_pcode_nf IN ('C6426', 'E4525', 'J2353', 'J5231', 'J525', 'M624', 'M6256', 'P4216', 'T5241')
  )
  AND (
    ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'actress')
  )
  AND (
    it1.id IN ('34')
  )
