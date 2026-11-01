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
    n.name_pcode_nf IN ('A5351', 'D1341', 'D5352', 'D6216', 'J1362', 'L2523', 'R5245', 'R5435', 'S5256', 'S5363', 'W4125')
    OR n.name_pcode_nf IS NULL
  )
  AND (
    ci.note IN ('(writer)') OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'director', 'writer')
  )
  AND (
    it1.id IN ('37')
  )
