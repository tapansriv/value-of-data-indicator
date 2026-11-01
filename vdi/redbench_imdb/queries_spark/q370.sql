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
    n.name_pcode_nf IN ('F6521', 'G6212', 'M2423', 'P3623', 'R1632', 'R2631', 'R2632')
    OR n.name_pcode_nf IS NULL
  )
  AND (
    ci.note IN ('(producer)', '(production assistant)') OR ci.note IS NULL
  )
  AND (
    rt.role IN ('composer', 'director', 'editor', 'miscellaneous crew', 'producer')
  )
  AND (
    it1.id IN ('31')
  )
