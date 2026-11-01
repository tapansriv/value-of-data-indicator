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
    n.name_pcode_nf IN ('A4163', 'A5362', 'B6524', 'B6535', 'C6231', 'F6521', 'M5456', 'R1632', 'R2631')
    OR n.name_pcode_nf IS NULL
  )
  AND (
    ci.note IN ('(executive producer)', '(producer)', '(production assistant)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('cinematographer', 'director', 'editor', 'miscellaneous crew', 'producer')
  )
  AND (
    it1.id IN ('31')
  )
