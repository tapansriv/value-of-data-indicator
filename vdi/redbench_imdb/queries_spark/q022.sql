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
    n.gender IN ('m')
  )
  AND (
    n.name_pcode_nf IN ('A5351', 'A6543', 'B2414', 'B6242', 'C5652', 'D165', 'E6463', 'G6262', 'J2123', 'J2524', 'K5425', 'M634', 'R1426', 'R2634', 'R2653', 'S5145', 'T563', 'V3535', 'W4264', 'W6535')
  )
  AND (
    ci.note IN ('(archive footage)', '(choreographer) (as Kamal)', '(executive producer)', '(production assistant)', '(uncredited)', '(voice)', '(writer)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'director', 'miscellaneous crew', 'producer', 'writer')
  )
  AND (
    it1.id IN ('31')
  )
