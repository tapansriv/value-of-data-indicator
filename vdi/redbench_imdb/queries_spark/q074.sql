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
    n.name_pcode_nf IN ('A5635', 'B623', 'C6526', 'E162', 'E4213', 'G6236', 'H546', 'I5362', 'J4163', 'J4265', 'J4514', 'K321', 'K6235', 'M2525', 'M2532', 'N3454', 'P253', 'R2414', 'S216', 'S242', 'S436', 'T3251', 'V5245')
  )
  AND (
    ci.note IN ('(credit only)', '(voice) (as E.G. Daily)', '(voice)', '(writer)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actress', 'writer')
  )
  AND (
    it1.id IN ('19')
  )
