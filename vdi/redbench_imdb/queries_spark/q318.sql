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
    n.name_pcode_nf IN ('A53', 'A5345', 'C6352', 'C6452', 'D1352', 'G6253', 'I641', 'J2165', 'J2516', 'J5353', 'P2651', 'R2563', 'S2312', 'S3154', 'T32', 'T5325', 'T56')
  )
  AND (
    ci.note IN ('(associate producer)', '(co-creator)', '(executive producer)', '(line producer)', '(producer)', '(producer: Fuji TV)', '(production accountant)', '(production assistant)', '(script supervisor)', '(supervising producer)', '(writer)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('director', 'miscellaneous crew', 'producer', 'production designer', 'writer')
  )
  AND (
    it1.id IN ('22')
  )
