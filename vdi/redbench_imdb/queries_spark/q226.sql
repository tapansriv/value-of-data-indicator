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
    n.name_pcode_nf IN ('C4213', 'C6231', 'D6362', 'E4534', 'G3524', 'I4352', 'J4346', 'J5161', 'J5412', 'K52', 'L2634', 'L2653', 'L6212', 'M6212', 'R1521', 'R2632', 'S325', 'S4256', 'W5341')
  )
  AND (
    ci.note IN ('(marketing and public relations)', '(producer)', '(production coordinator)', '(story consultant) (as Sally Sussman)', '(supervising director)', '(voice)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actress', 'director', 'miscellaneous crew', 'producer', 'writer')
  )
  AND (
    it1.id IN ('34')
  )
