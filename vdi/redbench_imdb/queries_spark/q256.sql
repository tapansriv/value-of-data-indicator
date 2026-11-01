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
    n.name_pcode_nf IN ('A2416', 'A5356', 'B6535', 'E4213', 'G6323', 'J252', 'J5145', 'K3152', 'L6512', 'M5345', 'M625', 'M6262', 'M6352', 'M6363', 'N6416', 'N6521', 'S123', 'S6523', 'V2535')
  )
  AND (
    ci.note IN ('(associate producer)', '(insurance broker)', '(producer)', '(production secretary)', '(segment producer)', '(story editor)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actress', 'composer', 'director', 'miscellaneous crew', 'producer')
  )
  AND (
    it1.id IN ('26')
  )
