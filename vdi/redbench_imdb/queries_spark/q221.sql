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
    n.gender IN ('f')
  )
  AND (
    n.name_pcode_nf IN ('D4151', 'D5136', 'E5421', 'K2353', 'K6231', 'N3536', 'N6153', 'S3246', 'S3535', 'V5316', 'V6325', 'Z612')
  )
  AND (
    ci.note IN ('(creator)', '(script supervisor)') OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actress', 'miscellaneous crew', 'writer')
  )
  AND (
    it1.id IN ('22')
  )
