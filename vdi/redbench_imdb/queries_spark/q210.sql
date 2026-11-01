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
    n.name_pcode_nf IN ('A3651', 'B463', 'C6421', 'E3451', 'J516', 'J5162', 'K1521', 'L262', 'M2436', 'V5215')
  )
  AND (
    ci.note IN ('(adaptation)', '(executive producer)', '(producer)', '(production accountant)', '(production coordinator)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('cinematographer', 'costume designer', 'director', 'miscellaneous crew', 'producer', 'writer')
  )
  AND (
    it1.id IN ('34')
  )
