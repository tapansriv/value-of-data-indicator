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
    n.name_pcode_nf IN ('A2463', 'A5326', 'D1326', 'D26', 'H6325', 'J2613', 'J565', 'O3423', 'W3235')
  )
  AND (
    ci.note IN ('(story editor)', '(writer)') OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'composer', 'miscellaneous crew', 'writer')
  )
  AND (
    it1.id IN ('31')
  )
