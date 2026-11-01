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
    n.name_pcode_nf IN ('A3651', 'A5352', 'C4514', 'E256', 'G6215', 'K6423', 'L65', 'P6125', 'P636', 'R2452', 'S1326', 'S2524')
  )
  AND (
    ci.note IN ('(as Audrey Bansmer)', '(executive producer)', '(uncredited)', '(written by)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'composer', 'costume designer', 'director', 'editor', 'producer', 'writer')
  )
  AND (
    it1.id IN ('37')
  )
