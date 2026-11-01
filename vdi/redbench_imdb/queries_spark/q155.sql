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
    n.name_pcode_nf IN ('A4163', 'A4253', 'C6231', 'G6212', 'M2423', 'M2425', 'M5456', 'P3623', 'R2632', 'S3152')
  )
  AND (
    ci.note IN ('(executive producer)', '(producer)', '(writer)') OR ci.note IS NULL
  )
  AND (
    rt.role IN ('composer', 'director', 'editor', 'producer', 'writer')
  )
  AND (
    it1.id IN ('25')
  )
