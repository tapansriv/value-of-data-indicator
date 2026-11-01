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
    n.name_pcode_nf IN ('A623', 'B4246', 'B5325', 'D5654', 'G2526', 'J2561', 'J52', 'L2124', 'M3632', 'M6212', 'N1453', 'N2423', 'O4165', 'O4652', 'Q5253', 'T5246', 'V4356', 'W2423')
  )
  AND (
    ci.note IN ('(as Cruz y Raya)', '(as Jason Robards)', '(producer)', '(switcher director)', '(uncredited)', '(voice)', '(voice: English version)', '(writer)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'composer', 'miscellaneous crew', 'producer', 'writer')
  )
  AND (
    it1.id IN ('26')
  )
