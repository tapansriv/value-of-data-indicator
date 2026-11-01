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
    n.name_pcode_nf IN ('C3652', 'J5163', 'J5165', 'K6525', 'L5321', 'M2416', 'M6251', 'M6523', 'M6524', 'M6562', 'V4535')
  )
  AND (
    ci.note IS NULL
  )
  AND (
    rt.role IN ('actress')
  )
  AND (
    it1.id IN ('22')
  )
