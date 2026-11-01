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
    n.name_pcode_nf IN ('A5325', 'A5632', 'C2414', 'C4535', 'D2151', 'E4534', 'E5434', 'H4626', 'H62', 'J5465', 'L2452', 'L654', 'M2421', 'M625', 'M6253', 'M6353', 'N5212', 'O4262', 'S4153', 'S5152', 'S6454', 'T62')
  )
  AND (
    ci.note IN ('(TV engineering unit head)', '(creator)', '(producer)', '(production secretary)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actress', 'composer', 'director', 'editor', 'miscellaneous crew', 'producer', 'writer')
  )
  AND (
    it1.id IN ('32')
  )
