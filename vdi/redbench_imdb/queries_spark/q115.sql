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
    n.gender IN ('f')
  )
  AND (
    n.name_pcode_nf IN ('A2545', 'A3615', 'A5215', 'A5245', 'C6424', 'D6243', 'E1514', 'F5345', 'H6525', 'I4512', 'J5232', 'M23', 'M5625', 'M6425', 'P2346', 'R3126', 'S2516', 'S5343', 'V2361', 'Z2134', 'Z6562')
  )
  AND (
    ci.note IN ('(archive footage)', '(as Zsazsa Padilla)', '(consulting producer)', '(head writer)', '(production secretary)', '(uncredited)', '(voice)', '(voice: English version)', '(writer)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actress', 'miscellaneous crew', 'producer', 'writer')
  )
  AND (
    it1.id IN ('22')
  )
