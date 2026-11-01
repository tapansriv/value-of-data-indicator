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
    n.name_pcode_nf IN ('A5365', 'B6531', 'I6525', 'J2516', 'K53', 'N2426', 'N5165', 'N6523', 'R1214', 'R2632', 'S1536', 'Y523', 'Y5252')
  )
  AND (
    ci.note IN ('(copying & shipping)', '(head writer story)', '(line producer)', '(producer)', '(production secretary)', '(story)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actress', 'director', 'miscellaneous crew', 'producer', 'writer')
  )
  AND (
    it1.id IN ('34')
  )
